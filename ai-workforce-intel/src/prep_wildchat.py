"""WildChat (Allen AI): conversation logs -> usage, adoption and enablement series.

The raw shards are large (WildChat-4.8M is ~12 GB), so this module streams one
Parquet row group at a time and keeps only small numeric fields. Conversation
text is read only to measure lengths and is never stored.

The schema differs slightly between WildChat versions (some fields are
top-level in one and per-turn in another), so every field is looked up
defensively and the report says which source was used.

Outputs (data/processed/):
  wildchat_conversations   one row per conversation (no text)
  wildchat_daily           day x model family: conversations, tokens, active/new users
  wildchat_weekly          week: usage + enablement proxies (new users, returning share, maturity)
  wildchat_monthly         month totals (for the monthly expenditure view)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RAW, FIGURES, save, log_quality, adf_summary  # noqa: E402

CHARS_PER_TOKEN = 4.0  # fallback estimate only when token counts are absent


def _turn_field(conv: pa.ChunkedArray | pa.Array, name: str):
    """Return (flattened per-turn values, parent row index) for a struct field, or None."""
    if isinstance(conv, pa.ChunkedArray):
        conv = conv.combine_chunks()
    struct_type = conv.type.value_type
    if name not in [f.name for f in struct_type]:
        return None
    flat = pc.list_flatten(conv)
    parents = pc.list_parent_indices(conv).to_numpy()
    return pc.struct_field(flat, name), parents


def process_table(t: pa.Table, used: dict) -> pd.DataFrame:
    n = t.num_rows
    names = t.column_names
    out = pd.DataFrame({
        "timestamp": pd.to_datetime(t.column("timestamp").to_pandas(), utc=True),
        "model": t.column("model").to_pandas().astype(str),
    })
    conv = t.column("conversation")

    # --- user identifier (hashed IP): top-level or first turn
    if "hashed_ip" in names:
        out["user_hash"] = t.column("hashed_ip").to_pandas().astype(str); used.setdefault("user_hash", set()).add("top-level hashed_ip")
    else:
        r = _turn_field(conv, "hashed_ip")
        if r is not None:
            vals, parents = r
            s = pd.Series(vals.to_pandas().values, index=parents)
            out["user_hash"] = s.groupby(level=0).first().reindex(range(n)).astype(str).values
            used.setdefault("user_hash", set()).add("per-turn hashed_ip (first turn)")
        else:
            out["user_hash"] = np.nan; used.setdefault("user_hash", set()).add("NOT AVAILABLE")

    for col in ("country", "language"):
        if col in names:
            out[col] = t.column(col).to_pandas()

    # --- per-turn role, token counts and lengths
    role = _turn_field(conv, "role")
    content = _turn_field(conv, "content")
    tokens = _turn_field(conv, "token_counter")
    lens = conv.combine_chunks() if isinstance(conv, pa.ChunkedArray) else conv
    out["n_turns_raw"] = pc.list_value_length(lens).to_numpy(zero_copy_only=False)

    if role is not None and content is not None:
        roles = role[0].to_pandas().values
        parents = role[1]
        chars = pc.utf8_length(pc.fill_null(content[0], "")).to_numpy(zero_copy_only=False)
        df = pd.DataFrame({"row": parents, "role": roles, "chars": chars})
        if tokens is not None:
            df["tok"] = tokens[0].to_pandas().values
            used.setdefault("tokens", set()).add("per-turn token_counter")
        else:
            df["tok"] = df["chars"] / CHARS_PER_TOKEN
            used.setdefault("tokens", set()).add(f"ESTIMATED from characters / {CHARS_PER_TOKEN}")
        df["tok_est"] = df["chars"] / CHARS_PER_TOKEN
        is_user = df["role"] == "user"
        g_user = df[is_user].groupby("row")
        g_asst = df[~is_user].groupby("row")
        out["user_turns"] = g_user.size().reindex(range(n), fill_value=0).values
        out["user_tokens"] = g_user["tok"].sum().reindex(range(n), fill_value=0).values
        out["assistant_tokens"] = g_asst["tok"].sum().reindex(range(n), fill_value=0).values
        out["user_tokens_charest"] = g_user["tok_est"].sum().reindex(range(n), fill_value=0).values
        out["first_prompt_tokens"] = g_user["tok_est"].first().reindex(range(n)).values
    else:
        used.setdefault("tokens", set()).add("NOT AVAILABLE (no role/content fields)")
        for c in ("user_turns", "user_tokens", "assistant_tokens", "user_tokens_charest", "first_prompt_tokens"):
            out[c] = np.nan
    return out


def load_conversations() -> pd.DataFrame:
    files = sorted((RAW / "wildchat").rglob("*.parquet"))
    if not files:
        raise FileNotFoundError("No WildChat Parquet shards in data/raw/wildchat - run download.py")
    used: dict = {}
    parts = []
    for i, f in enumerate(files, 1):
        pf = pq.ParquetFile(f)
        want = [c for c in ("timestamp", "model", "conversation", "hashed_ip", "country", "language")
                if c in pf.schema_arrow.names]
        for rg in range(pf.num_row_groups):
            parts.append(process_table(pf.read_row_group(rg, columns=want), used))
        print(f"  shard {i}/{len(files)}: {f.name}")
    d = pd.concat(parts, ignore_index=True)
    sources = {k: sorted(v) for k, v in used.items()}
    log_quality("WildChat", shards=len(files), field_sources=sources)
    if len(sources.get("tokens", [])) > 1:
        log_quality("WildChat", WARNING="token counts come from different methods across shards; "
                    "use user_tokens_charest for a consistent series")
    return d


def clean(d: pd.DataFrame) -> pd.DataFrame:
    n0 = len(d)
    d = d.dropna(subset=["timestamp"])
    d = d[d["user_turns"].fillna(1) > 0]  # drop conversations with no user turn
    d["model_family"] = np.where(d["model"].str.contains("gpt-4|o1|o3|o4", case=False, regex=True),
                                 "gpt4_family", "gpt35_family")
    d["total_tokens"] = d["user_tokens"].fillna(0) + d["assistant_tokens"].fillna(0)
    d["date"] = d["timestamp"].dt.tz_convert("UTC").dt.floor("D").dt.tz_localize(None)
    d["week"] = d["date"].dt.to_period("W-SUN").dt.start_time
    d["month"] = d["date"].dt.to_period("M").dt.to_timestamp()
    has_user = d["user_hash"].notna() & (d["user_hash"] != "nan")
    first_seen = d[has_user].groupby("user_hash")["date"].min().rename("user_first_date")
    d = d.merge(first_seen, on="user_hash", how="left")
    d["is_first_conversation_day"] = d["date"] == d["user_first_date"]
    d = d.sort_values("timestamp")
    log_quality("WildChat",
                rows_raw=n0, rows_clean=len(d),
                period=f"{d['date'].min().date()} to {d['date'].max().date()}",
                models=d["model"].value_counts().head(10).to_dict(),
                users_with_hash=int(first_seen.size),
                user_id_caveat="hashed IP is an imperfect user ID (shared/changing IPs)",
                token_check="compare user_tokens vs user_tokens_charest in wildchat_conversations")
    return d


def daily(d: pd.DataFrame) -> pd.DataFrame:
    g = d.groupby(["date", "model_family"])
    out = g.agg(conversations=("timestamp", "size"), total_tokens=("total_tokens", "sum"),
                user_tokens=("user_tokens", "sum"), assistant_tokens=("assistant_tokens", "sum"),
                active_users=("user_hash", "nunique")).reset_index()
    new = (d[d["is_first_conversation_day"]].groupby(["date", "model_family"])["user_hash"]
           .nunique().rename("new_users"))
    out = out.merge(new, on=["date", "model_family"], how="left").fillna({"new_users": 0})
    full = pd.MultiIndex.from_product(
        [pd.date_range(d["date"].min(), d["date"].max(), freq="D"), sorted(d["model_family"].unique())],
        names=["date", "model_family"])
    out = out.set_index(["date", "model_family"]).reindex(full).reset_index()
    out["missing_day"] = out["conversations"].isna()
    return out.fillna(0)


def weekly(d: pd.DataFrame) -> pd.DataFrame:
    w = d.groupby("week").agg(conversations=("timestamp", "size"), total_tokens=("total_tokens", "sum"),
                              active_users=("user_hash", "nunique"),
                              avg_user_turns=("user_turns", "mean"),
                              median_first_prompt_tokens=("first_prompt_tokens", "median"))
    new_users = d[d["is_first_conversation_day"]].groupby("week")["user_hash"].nunique()
    w["new_users"] = new_users.reindex(w.index, fill_value=0)
    # returning share: active users this week who were first seen in an EARLIER week
    first_week = d.groupby("user_hash")["week"].min()
    dd = d[["week", "user_hash"]].drop_duplicates()
    dd["returning"] = dd["week"] > dd["user_hash"].map(first_week)
    w["returning_users"] = dd.groupby("week")["returning"].sum().reindex(w.index, fill_value=0)
    w["returning_share"] = w["returning_users"] / w["active_users"].replace(0, np.nan)
    w["tokens_per_active_user"] = w["total_tokens"] / w["active_users"].replace(0, np.nan)
    w = w.reset_index()
    # Partial first/last weeks distort trends - flag them.
    days = d.groupby("week")["date"].nunique()
    w["partial_week"] = w["week"].map(days).fillna(0) < 7
    return w


def monthly(d: pd.DataFrame) -> pd.DataFrame:
    m = d.groupby(["month", "model_family"]).agg(conversations=("timestamp", "size"),
                                                 total_tokens=("total_tokens", "sum"),
                                                 active_users=("user_hash", "nunique")).reset_index()
    days = d.groupby("month")["date"].nunique()
    m["days_observed"] = m["month"].map(days)
    m["days_in_month"] = m["month"].dt.days_in_month
    m["partial_month"] = m["days_observed"] < m["days_in_month"]
    return m


def plots(w: pd.DataFrame):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    w = w[~w["partial_week"]]
    fig, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    axes[0].plot(w["week"], w["total_tokens"] / 1e6)
    axes[0].set(title="WildChat weekly tokens", ylabel="Million tokens")
    axes[1].plot(w["week"], w["new_users"], label="New users")
    axes[1].plot(w["week"], w["returning_users"], label="Returning users")
    axes[1].set(title="Weekly new vs returning users (enablement proxy)", ylabel="Users")
    axes[1].legend(frameon=False)
    fig.tight_layout(); fig.savefig(FIGURES / "wildchat_weekly.png", dpi=150); plt.close(fig)


def run():
    print("WildChat")
    d = clean(load_conversations())
    keep = ["timestamp", "date", "model", "model_family", "user_hash", "country", "language",
            "n_turns_raw", "user_turns", "user_tokens", "assistant_tokens", "total_tokens",
            "user_tokens_charest", "first_prompt_tokens", "is_first_conversation_day"]
    save(d[[c for c in keep if c in d.columns]], "wildchat_conversations")
    dl = daily(d); save(dl, "wildchat_daily")
    w = weekly(d); save(w, "wildchat_weekly")
    save(monthly(d), "wildchat_monthly")
    tot = dl.groupby("date")["total_tokens"].sum()
    log_quality("WildChat", missing_days=int(dl.groupby("date")["missing_day"].all().sum()),
                adf_daily_total_tokens=adf_summary(tot),
                adf_weekly_new_users=adf_summary(w.loc[~w["partial_week"], "new_users"]))
    plots(w)


if __name__ == "__main__":
    run()
