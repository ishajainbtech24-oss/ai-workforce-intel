"""Every piece of on-screen text, plus the one mapping from engine names to plain labels.

Written for a manager with no technical background: short sentences, everyday words, what a
result MEANS. Templates use str.format with values filled in from the real results.
"""
from __future__ import annotations

PRODUCT = "AI Workforce Investment Intelligence"
EXAMPLE_PILL = "Example company"
BANNER = ("You are looking at an example company with made-up figures. "
          "Change them on the Try your own numbers page.")
FOOTER = "AI Workforce Investment Intelligence. Figures are estimates, not promises."

# ---- one mapping from engine names to plain labels (used everywhere) ----
OUTLOOK = {"downside": "Cautious outlook", "expected": "Expected outlook", "optimistic": "Optimistic outlook"}
OUTLOOK_SHORT = {"downside": "Cautious", "expected": "Expected", "optimistic": "Optimistic"}
CAUTION = {1.0: "Standard", 1.5: "More cautious", 2.0: "Most cautious"}
LINE = {"token_expenditure": "AI usage cost", "hosting": "Technology running costs",
        "enablement": "Training and support", "integration": "Setup and connection work"}
LINE_TAG = {"token_expenditure": "Based on trends", "hosting": "Based on trends",
            "enablement": "Our estimate", "integration": "Our estimate"}
TYPE_TAG = {"Forecast-driven": "Based on trends", "Estimate": "Our estimate", "Projection": "Estimated benefit"}
LEVER = {"time_saved_parameter": "Time saved per person",
         "realisation_rate": "Share of saved time that becomes value",
         "training_hours_per_new_user": "Training hours per new user",
         "engineering_hours_build": "Setup effort",
         "base_wages": "Pay levels",
         "employees": "Number of employees",
         "adoption_target": "Adoption by the end of the ramp",
         "tokens_per_active_user_per_month": "AI usage per person"}

# ---- pages ----
PAGES = {"welcome": ("Welcome", ":material/waving_hand:"),
         "overview": ("The big picture", ":material/space_dashboard:"),
         "data": ("The data we used", ":material/dataset:"),
         "forecast": ("What we expect next", ":material/trending_up:"),
         "reliable": ("How reliable it is", ":material/fact_check:"),
         "costs": ("Where the money goes", ":material/payments:"),
         "timing": ("When it pays for itself", ":material/event_available:"),
         "levers": ("What matters most", ":material/tune:"),
         "company": ("Try your own numbers", ":material/edit_note:")}

HERO_TITLE = "See what an AI programme could cost, what it could return, and when it could pay for itself."
HERO_SUB = "Built on public trends in pay, technology prices and AI use, applied to an example company."

KPI = {"cost": ("Total cost over the year", "Everything the programme costs in 12 months."),
       "benefit": ("Estimated benefit over the year", "The value of time people save, as an estimate."),
       "balance": ("Running balance at year end", "Benefit minus cost, added up month by month."),
       "payback": ("Pays for itself", "The month the running balance turns positive.")}
NOT_WITHIN = "Not within {months} months"
MONTH = "Month {month}"

OVERVIEW_CHART_TITLE = "Running balance over the year, by outlook"
AXIS_BALANCE, AXIS_AMOUNT = "Running balance (₹)", "Amount (₹)"
AXIS_COST_MONTH, AXIS_CHANGE = "Cost per month (₹)", "Change in year-end<br>balance (₹)"
ZERO_LINE = "Pays for itself above this line"
VIEW_RANGE, VIEW_TYPICAL = "Likely range", "Typical case only"
FINDINGS_TITLE = "Key findings"
FINDING_COST = ("Training and support is the biggest cost: {share} of all spending in the expected outlook. "
                "Most of the money goes on people, not technology.")
FINDING_LEVERS = ("What moves the result most: {first} and {second}. "
                  "A 20% change in either shifts the year-end balance by about {swing}.")
FINDING_TECH = ("Technology running costs and AI usage are small and steady ({share} of the cost). "
                "The company's own choices matter far more than technology prices.")

HOW_TO_READ = {
    "data": "Pick a trend at the top. What happened shows every real value used. Repeating pattern shows the average "
            "for each hour, day, month or quarter, so you can see whether some times are usually higher. Unusual "
            "points lists values that were far from what the usual pattern suggests; they were kept in the data.",
    "reliable": "Pick a trend at the top. The chart shows the most recent real values that were held back: the solid "
                "line is what really happened, the dotted line is what was predicted, and the band is the range given "
                "with that prediction. Dots show whether each real value landed inside the range. The bars below "
                "compare every approach we tried, by how far off it was on average in earlier checks.",
    "forecast": "Pick a trend at the top. The solid line is what really happened, up to the latest real value. The "
                "dashed line is what we expect next, and the shaded band is the likely range: where eight in ten of "
                "the futures we looked at land. Each trend was looked ahead only as far as shown here.",
    "welcome": "The solid line is what really happened. The dashed line after Today is what we expect, and the shaded "
               "band is the likely range: where eight in ten of the futures we looked at land. The band widens "
               "because the further ahead we look, the less sure we can be.",
    "overview": "Each line shows the running balance: benefit minus cost, added up month by month. Below zero "
                "means money is still tied up; above zero means the programme has paid for itself. The shaded "
                "band is the likely range.",
    "costs": "Bars show what is spent each month. Lines marked Based on trends follow public price and pay "
             "trends; lines marked Our estimate come from the company's own plans.",
    "timing": "We looked at many possible futures. The chart shows in which month the programme pays for "
              "itself in each of them, and how often it does not within the year.",
    "levers": "Each bar shows how much the year-end balance changes if one choice is 20% lower or 20% higher, "
              "with everything else kept the same. Longer bars mark the choices that matter most.",
    "company": "Enter your own figures and press Update results. Everything on this page is an estimate from "
               "the numbers you entered.",
}

COSTS_TITLE = "Where the money goes"
OUTLOOK_PICK, CAUTION_PICK = "Outlook", "How cautious to be about the future"
CAUTION_HELP = "More cautious widens the range of possible futures for pay and technology prices."
COST_STACK_TITLE = "Monthly cost by type"
DONUT_TITLE = "Share of total cost"
BENEFIT_COST_TITLE = "Estimated benefit and cost each month"
INCLUDED_TITLE = "What is included"
INCLUDED = {"token_expenditure": "The cost of people using AI tools, based on how much they use them and the price.",
            "hosting": "Servers and other technology needed to run the tools, following technology price trends.",
            "enablement": "Training new users, refresher sessions, and a monthly support budget.",
            "integration": "Engineering work to set the tools up and connect them, then keep them running."}

TIMING_TITLE = "When does it pay for itself?"
VERDICT_YES = ("In {share} of the futures we looked at, the programme pays for itself within {months} months, "
               "typically by month {month}.")
VERDICT_NO = "In none of the futures we looked at does the programme pay for itself within {months} months."
TIMING_CHART_TITLE = "Month the programme pays for itself"
TIMING_AXIS_X, TIMING_AXIS_Y = "Month", "Share of futures"
COMPARE_TITLE = "The three outlooks side by side"
COMPARE_COLS = ["Outlook", "Chance it pays for itself", "Typical month", "Likely year-end balance",
                "Most money tied up at once"]
NARROW_NOTE = ("The range is narrow because the cost trends we track move steadily; the bigger uncertainty is in "
               "the company's own choices (see What matters most).")

LEVERS_TITLE = "Which choices change the result most"
LEVER_LOW, LEVER_HIGH = "20% lower", "20% higher"
LEVER_TIP = "If this were {direction}, the year-end balance would be {value}"
LEVER_TAKEAWAY = ("The three choices that matter most are {a}, {b} and {c}. Getting these right matters far more "
                  "than technology prices.")
NO_PAYBACK_BOX_TITLE = "What could change that"
NO_PAYBACK = ("At the example figures, the expected outlook does not pay for itself within {months} months. "
              "The year-end running balance is {balance}.")
NO_PAYBACK_LEVERS = "The two choices that would help most: {a}, and {b}."
RAISE, LOWER = "raising", "lowering"

COMPANY_TITLE = "Your company"
COMPANY_NOTE = "These results are estimates from the numbers you entered."
OUTLOOK_CHART_TITLE_YOURS = "Your running balance"
UPDATE, RESET, DOWNLOAD = "Update results", "Reset to example", "Download my results"
WORKING = "Working out the numbers..."
FIELDS = {"employees": ("Employees", "people", "People in scope of the programme."),
          "adoption_target": ("Share using AI at the end", "%", "Share of employees using AI once the roll-out is done."),
          "ramp_months": ("Months to reach it", "months", "How long the roll-out takes."),
          "training_hours_per_new_user": ("Training hours per new user", "hours", "One-off training for each new user."),
          "engineering_hours_build": ("Setup effort", "hours", "Engineering hours to set the tools up and connect them."),
          "realisation_rate": ("How much saved time becomes value", "%", "Some saved time is used for other work; this is the share that adds value."),
          "fixed_enablement_cost_per_month": ("Monthly training and support budget", "₹ per month", "Trainers, licences and support staff."),
          "base_hourly_wage_staff": ("Hourly pay for staff", "₹ per hour", "Fully loaded cost per hour."),
          "base_hourly_wage_engineer": ("Hourly pay for engineers", "₹ per hour", "Fully loaded cost per hour."),
          "tokens_per_active_user_per_month": ("AI usage per person per month", "units", "How much each person uses AI tools each month, in usage units."),
          "fixed_token_price_per_mtok": ("AI usage price", "₹ per million units", "What one million units of AI usage cost. Ask your provider for this."),
          "base_monthly_hosting_cost": ("Technology running cost", "₹ per month", "Servers and tools needed today."),
          "horizon_months": ("Project length", "months", "How many months to look ahead (6 to 24).")}
OUTLOOK_FIELD = ("Time saved outlook", "How much working time people save with AI.")
ERRORS = {"employees": "Employees cannot be negative.", "share": "Shares must be between 0% and 100%.",
          "generic": "Some numbers need a second look: {detail}"}
DOWNLOAD_COLS = {"month": "Month", "cost": "Total cost (₹)", "benefit": "Estimated benefit (₹)",
                 "balance": "Running balance (₹)"}
KPI_YOURS = {"cost": "Total cost", "benefit": "Estimated benefit", "balance": "Running balance at the end",
             "payback": "Pays for itself"}
KPI_YOURS_MEANING = {"cost": "Everything the programme costs over the project.",
                     "benefit": "The value of time people save, as an estimate.",
                     "balance": "Benefit minus cost at the end of the project.",
                     "payback": "The month the running balance turns positive."}

# ---- UI polish (Phase 5B): switches, status chips, 3D views ----
DARK_MODE, REDUCE_MOTION, PAGES_MENU = "Dark mode", "Reduce motion", "Menu"
DARK_HELP = "Switch between a light and a dark page. Kept while this window is open."
MOTION_HELP = "Turn off moving and 3D pictures. A calm, still version is shown instead."
CHIP = {"good": "On track", "attention": "Needs attention", "estimate": "Estimate", "people": "Mostly people costs"}
LOWEST_POINT = "Lowest point: {value}"
PAYS_MARK = "Pays for itself: month {month}"
FLOW_TITLE = "Year-end running balance, by outlook"
FLOW_HINT = "Drag to turn. Columns below the floor have not paid for themselves yet."
FLOW_FLAT_TITLE = "The same figures as plain bars"
FLOW_FLOOR = "Break-even floor"
FLOW_TIP_GOOD = "Above the floor: it has paid for itself by the year end."
FLOW_TIP_BAD = "Below the floor: it has not paid for itself by the year end."
SLICE_TIP = "{amount}, {share} of the total cost"
DONUT_VIEW = ("3D view", "Flat view")
DONUT_VIEW_LABEL = "How to show the cost split"
DONUT_HINT = "Point at a slice to see its amount."
DEPTH_TITLE = "How far each choice can move the year-end balance"
DEPTH_NOTE = "Gap between the result with the choice 20% lower and 20% higher."
LEVERS_CHART_TITLE = "If each choice were 20% lower or 20% higher"
FOOTER_NOTE = "Example company with made-up figures."

# ---- Phase 5D: navigation groups, Welcome page, "Next" cards ----
SECTION_MONEY = "The money"
SECTION_YOURS = "Your own figures"
WELCOME_CTA, WELCOME_HOW = "Explore the results", "How it works"
WELCOME_CHART_TITLE = "Technology hosting prices: what happened and what we expect"
WELCOME_CHART_NOTE = ("Price level of hosting services (December 2000 = 100). We expect about {value} by {end}, "
                      "likely between {low} and {high}.")
WELCOME_STEPS_TITLE = "How it works"
WELCOME_STEPS = [("Real public trends", "Pay, technology prices and AI use, taken from public records."),
                 ("What we expect next", "Each trend carried forward, with a likely range around it."),
                 ("What it means for you", "Cost, estimated benefit and when the programme could pay for itself.")]
WELCOME_NUMBERS_TITLE = "The example company at a glance"
WELCOME_PAYS_NOTE = "Optimistic outlook: month {month}"
WELCOME_PAYS_NONE = "None of the outlooks within {months} months"
LEGEND_HAPPENED, LEGEND_EXPECT, LEGEND_RANGE = "What happened", "What we expect", "Likely range (8 in 10)"
TODAY = "Today"
AXIS_PRICE_LEVEL = "Price level"
HOVER_EXPECT = "We expect {value}, likely between {low} and {high}"
NEXT_LABEL = "Next"
NEXT = {"welcome": ("overview", "The four numbers that matter, and how the running balance moves over the year."),
        "overview": ("data", "The real public records behind every forecast, and anything unusual in them."),
        "data": ("forecast", "What the public trends behind the costs are expected to do next."),
        "forecast": ("reliable", "How close earlier predictions came to what really happened."),
        "reliable": ("costs", "What the money is spent on, month by month."),
        "costs": ("timing", "In which month the programme could pay for itself."),
        "timing": ("levers", "Which choices change the result the most."),
        "levers": ("company", "Put in your own figures and see the result.")}

# ---- Phase 5D: the seven real series and the approaches compared (plain names; engine names only as keys) ----
# name, one-line description, unit word(s) for values, axis label
SERIES = {
    "eci_wages_quarterly": ("Pay levels", "How much US employers pay per hour of work, as a level that tracks change "
                            "over time.", "points", "Pay level"),
    "ppi_hosting_monthly": ("Technology hosting prices", "What US firms charge for hosting and running computer "
                            "services, as a level (December 2000 = 100).", "points", "Price level"),
    "burst_tokens_total_daily": ("AI usage per day", "Units of AI usage per day at one large AI service, "
                                 "apps and chat together.", "usage units", "Usage units per day"),
    "burst_tokens_api_daily": ("AI usage through apps", "Units of AI usage per day sent by other software "
                               "connected to the service.", "usage units", "Usage units per day"),
    "burst_tokens_chat_daily": ("AI usage in chat", "Units of AI usage per day typed by people in a chat window.",
                                "usage units", "Usage units per day"),
    "burst_requests_hourly": ("AI requests per hour", "How many questions people and software sent to the AI "
                              "service each hour.", "requests", "Requests per hour"),
    "wildchat_conversations_daily": ("Chat conversations per day", "Conversations started each day on a free "
                                     "public AI chat site.", "conversations", "Conversations per day"),
}
SERIES_GROUPS = {"Pay and prices": ["eci_wages_quarterly", "ppi_hosting_monthly"],
                 "AI use": ["burst_tokens_total_daily", "burst_tokens_api_daily", "burst_tokens_chat_daily",
                            "burst_requests_hourly", "wildchat_conversations_daily"]}
NO_DATES = "The source does not give calendar dates, so days are numbered from the first one."
STEP = {"hour": "Hour {n}", "day": "Day {n}"}
GRAIN_WORD = {"hour": ("hour", "hours"), "day": ("day", "days"), "month": ("month", "months"),
              "quarter": ("quarter", "quarters")}
# slot and cycle used by the 'repeat the pattern' approaches, per grain
CYCLE = {"hour": ("hour", "day"), "day": ("weekday", "week"), "month": ("month", "year"), "quarter": ("quarter", "year")}
APPROACH = {
    "naive": "Repeat the last value",
    "seasonal_naive": "Repeat the same {slot} last {cycle}",
    "mean": "Long-run average",
    "drift": "Straight-line trend",
    "seasonal_ma3": "Average of the same {slot} in the last three {cycle}s",
    "moving_average": "Recent average",
    "ses": "Smoothed recent values",
    "holt": "Smoothed trend",
    "damped_holt": "Smoothed trend that levels off",
    "hw_additive": "Smoothed trend with a repeating pattern",
    "hw_multiplicative": "Smoothed trend with a repeating pattern that grows with the level",
    "arima": "Statistical pattern finder",
    "sarima": "Statistical pattern finder with a repeating cycle",
    "sarimax": "Statistical pattern finder using outside information",
    "ridge": "Learning from past values (simple)",
    "random_forest": "Learning from past values (many decision trees)",
    "xgboost": "Learning from past values (boosted trees)",
    "ridge_with_requests": "Learning from past values and request counts (simple)",
    "random_forest_with_requests": "Learning from past values and request counts (many decision trees)",
    "xgboost_with_requests": "Learning from past values and request counts (boosted trees)",
    "prophet": "Trend-and-calendar approach",
    "lstm": "Neural network",
    "ensemble": "Blend of several approaches",
}
REFERENCE_APPROACH = "seasonal_naive"  # the simple yardstick every chosen approach was compared with
# per-grain wording of the two 'repeat the pattern' approaches (used before the generic template above)
APPROACH_BY_GRAIN = {
    "seasonal_naive": {"hour": "Repeat the same hour the day before", "day": "Repeat the same weekday last week",
                       "month": "Repeat the same month last year", "quarter": "Repeat the same quarter last year"},
    "seasonal_ma3": {"hour": "Average of the same hour over the last three days",
                     "day": "Average of the same weekday in the last three weeks",
                     "month": "Average of the same month in the last three years",
                     "quarter": "Average of the same quarter in the last three years"},
}

# ---- Phase 5D step C: What we expect next ----
SECTION_FORECASTS = "Forecasts"
FORECAST_TITLE = "What we expect next"
FORECAST_SUB = "Pick a trend to see what really happened, what we expect next, and the likely range around it."
PICK_SERIES, PICK_LENGTH = "Which trend", "Show the next"
LAST_REAL = "Latest real value"
AXIS_STEP = {"hour": "Hour", "day": "Day"}
FORECAST_HEADLINE = "By {end} we expect about {value} {unit}."
FORECAST_RANGE = "Likely between {low} and {high}."
FORECAST_CHANGE = "That is {change} compared with the latest real value ({last}, {when})."
SAME = "about the same"
RANGE_NOTE = "Likely range: where eight in ten of the futures we looked at land."
RANGE_WARN = ("When we checked earlier predictions, the real value landed inside the likely range only {inside} of "
              "{n} times. Treat the range as narrower than reality.")
RANGE_OK = "When we checked earlier predictions, the real value landed inside the likely range {inside} of {n} times."
DOWNLOAD_EXPECT = "Download what we expect"
EXPECT_COLS = {"when": "When", "expected": "We expect", "low": "Likely low", "high": "Likely high"}

# ---- Phase 5D step D: How reliable it is ----
RELIABLE_TITLE = "How reliable it is"
RELIABLE_SUB = ("Before trusting what we expect, see how close earlier predictions came. We held back the most recent "
                "real values, predicted them as if they were still in the future, and then compared.")
RELIABLE_VERDICT = ("Over the last {n} {grains} we held back, the prediction missed by about {miss} {unit} on average, "
                    "about {share} of the typical level.")
TILE_MISS = ("Average miss", "On the {n} {grains} held back. Typical level: {level}.")
TILE_INSIDE = ("Real value inside the likely range", "The range used on What we expect next. The range given with "
               "this first prediction caught {first} of {n}.")
TILE_VS = ("Compared with simply repeating", "Our misses were {size} the simple guess's "
           "(\"{reference}\"), over earlier checks.")
VALUE_OF = "{inside} of {n}"
VALUE_SMALLER = "{share} smaller miss"
VALUE_LARGER = "{share} larger miss"
PAST_CHART_TITLE = "What was predicted, and what really happened"
LEGEND_REAL, LEGEND_PREDICTED = "What really happened", "What was predicted"
LEGEND_RANGE_THEN = "Range given with the prediction"
LEGEND_INSIDE, LEGEND_OUTSIDE = "Inside the range", "Outside the range"
PREDICTED_HERE = "Prediction made here"
HOVER_PAST = "{when}: predicted {predicted}, really {actual}"
RANK_TITLE = "Which approach came closest"
RANK_SUB = "Average miss over the earlier checks, closest first. Shorter bars mean smaller misses."
RANK_USED, RANK_REFERENCE = "used", "simple yardstick"
RANK_SHOW_ALL = "Show every approach"
RANK_CLOSE = ("The {k} closest approaches missed by almost the same amount (within 5% of each other), so the choice "
              "between them matters little.")
RANK_NOT_FIRST = ("We used \"{chosen}\": its average miss was within {gap} of the closest, and it is the simpler "
                  "choice.")
RANK_SKIPPED = "{k} other approaches could not run on this data and are not shown."
AXIS_MISS = "Average miss ({unit})"

# ---- Phase 5D step F: The big picture and When it pays for itself ----
OVERVIEW_TITLE = "The big picture"
OVERVIEW_SUB = ("The four numbers that matter for the example company, how the running balance moves over the year, "
                "and which choices to look at first.")
DECIDE_TITLE = "What needs a decision"
DECIDE_SUB = "The choices that move the year-end balance most."
DECIDE_GAP = "From 20% lower to 20% higher, the year-end balance moves by {swing}."
DECIDE_HELPS = "Helps most: {phrase}."
STRIP_TITLE = "The trends behind the costs"
STRIP_CHANGE = "{change} by {end}"
STRIP_MEANING = "Expected change from the latest real value ({when})."
STRIP_RELIABLE_TITLE = "How close past predictions came"
STRIP_RELIABLE = ("Pay levels: about {pay} off on average. Hosting prices: about {host}. AI usage was much harder to "
                  "predict: {lo} to {hi} off.")
STRIP_LINK_EXPECT, STRIP_LINK_RELIABLE = "What we expect next", "How reliable it is"
SEE_3D = "See the year-end balance in 3D"
TIMING_DOTS_TITLE = "When each outlook pays for itself"
DOT_TIP_YES = ("{outlook}: typically pays for itself in month {month}; {share} of the futures we looked at pay for "
               "themselves within {months} months")
DOT_TIP_NO = "{outlook}: does not pay for itself within {months} months in {share} of the futures we looked at"
DOT_NONE = "Not within {months} months"

# ---- Phase 5D step E: The data we used ----
DATA_TITLE = "The data we used"
DATA_SUB = ("These are the real public records behind every forecast in this dashboard. Pick one to see what it holds, "
            "how it moved, and anything unusual in it.")
DATA_TILES = {"span": ("Time span", "{start} to {end}"), "count": ("Points", "{n} {grains}"),
              "unusual": ("Unusual points", "{k}"), "missing": ("Missing values", "{k}")}
DATA_TILE_MEANING = {"span": "First and last real value used.", "count": "One value per {grain}.",
                     "unusual": "Far from what the usual pattern suggests; kept, not removed.",
                     "missing": "Gaps inside the stretch used."}
NONE = "0"  # counts of zero (the word "None" is kept off the screen: it would look like a program value)
WINDOW_NOTE = {
    "full": "All {n} values in the source are used.",
    "burst": ("The source has values for {source} {grains}; the forecasts use the first {n}, because the {grains} after that "
              "include copies of earlier {grains} and a long run of unusually low activity."),
    "wildchat": ("The source has values for {source} days; the forecasts use the longest stretch in which both chat "
                 "services in the source had data ({n} days). The last day in the file was incomplete and is left out."),
}
OUTAGE_NOTE = "{when} was a known one-day outage at the source. It is kept in the data and marked on the chart."
DATA_TABS = ("What happened", "Repeating pattern", "Unusual points")
PLAIN_SUMMARY = ("The first {s} {grains} averaged about {first} {unit} and the last {s} about {last} {unit}, so the "
                 "values {direction}. Long-term trend: {trend}. Repeating {cycle} pattern: {pattern}.")
DIRECTION = {"up": "rose", "down": "fell", "flat": "stayed about the same"}
STRENGTH = {"strong": "strong", "some": "some", "little": "little"}
CYCLE_NAME = {"hour": "daily", "day": "weekly", "month": "yearly", "quarter": "yearly"}
PATTERN_TITLE = {"hour": "Average for each hour of the day", "day": "Average for each day of the week",
                 "month": "Average for each month of the year", "quarter": "Average for each quarter of the year"}
PATTERN_NOTE_UNDATED = "Days are counted from the first day in the source, so the days of the week are not named."
POSITION = {"hour": "{k}", "day": "{k}"}
POSITION_AXIS = {"hour": "Hour of the day (1 = first hour in the source)",
                 "day": "Day of the week (1 = first day in the source)"}
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MARK_UNUSUAL, MARK_OUTAGE = "Unusual point", "Known outage"
UNUSUAL_INTRO = ("Unusual points are values far from what the usual pattern suggests. They were kept in the data, "
                 "not removed.")
UNUSUAL_NONE = "No unusual points were found in this trend."
UNUSUAL_TOP = "Showing the {k} most unusual of {n}."
UNUSUAL_COLS = {"when": "When", "value": "Value", "how": "How unusual", "side": "Compared with usual"}
UNUSUAL_HOW = {"very": "Very unusual", "some": "Unusual"}
UNUSUAL_SIDE = {"high": "Higher", "low": "Lower"}
DOWNLOAD_DATA = "Download this trend's data"
DATA_COLS = {"when": "When", "value": "Value"}

# ---- Beginner pass: a guide under every chart, hints on controls, a glossary on every page ----
GUIDE_LABELS = ("What you see", "What it means", "Why it matters")
GUIDE = {
    "welcome": ("Hosting prices month by month. The solid line is what happened; after Today, the dashed line is what "
                "we expect and the band is the likely range.",
                "Prices are expected to {direction} {change} over the next {n} months, to about {pct_base} "
                "their December 2000 level.",
                "Hosting prices drive the programme's technology running costs."),
    "balance": ("The money in minus the money out, added up month by month, for three views of how much time AI "
                "saves.",
                "{story}",
                "Below the zero line, the programme has cost more than it has returned so far."),
    "year_end": ("Where each of the three outlooks stands after {months} months.",
                 "Outlooks ending above zero: {good} of 3. The gap between the best and the worst is {gap}.",
                 "The spread shows how much the result depends on how much time people really save."),
    "data_history": ("Every real value used: {n} {grains}. Amber dots mark unusual points.",
                     "Over the period the values {direction}; the long-term trend is {trend}.",
                     "This is the past that every forecast starts from: what we expect next carries it forward."),
    "data_pattern": ("The average for each {slot}, over all the real values used.",
                     "The highest average is {hi_label} and the lowest is {lo_label}, {gap} lower. The repeating "
                     "pattern is {strength}.",
                     "A strong repeating pattern means some {slots} are reliably busier than others, and the "
                     "forecast repeats it."),
    "forecast": ("Recent real values (solid), then what we expect (dashed) with the likely range (band).",
                 "{name}: {direction_words} over the next {n} {grains}. The likely range is {width} "
                 "({spread} by the end).",
                 "{feeds}"),
    "past": ("We hid the last {n} {grains}, predicted them as if they were still in the future, then compared.",
             "The real value landed inside the range given at the time {inside} of {n} times. The prediction "
             "was {bias} most of the time.",
             "It shows how far to trust what we expect next: big misses mean treat forecasts as rough guides."),
    "ranking": ("Every approach we tried, with its average miss in earlier checks. Shorter bars are better.",
                "The approach used made misses {size} the simple guess's.{close}",
                "Beating a simple guess means the forecast adds real information, not just a copy of the past."),
    "cost_stack": ("What is spent each month, split into four types of cost.",
                   "Spending peaks at {peak} in month {peak_month} while the setup work runs, then settles at about "
                   "{late} a month.",
                   "It shows when the most cash is needed."),
    "donut": ("How the total cost for the year splits by type.",
              "{biggest} is the largest part: {share} of the total.",
              "The largest part is where any saving would count most."),
    "benefit_cost": ("Estimated benefit (line) against cost (bars), month by month.",
                     "{story}",
                     "Once the monthly benefit is above the monthly cost, the running balance starts to recover."),
    "timing_dots": ("The typical month in which each outlook pays for itself.",
                    "{story}",
                    "It tells how long money stays tied up before the programme pays back."),
    "timing_bars": ("In which month the programme pays for itself, across the {runs} futures we looked at.",
                    "{story}",
                    "A tall bar at Not within {months} months means the programme usually needs longer than that."),
    "levers_depth": ("How far each choice can move the year-end balance, from 20% lower to 20% higher.",
                     "{a} and {b} matter most: each can move it by {swing}.",
                     "Effort spent on these choices changes the result far more than on the others."),
    "levers_chart": ("What happens to the year-end balance if one choice is 20% lower (orange) or 20% higher "
                     "(blue), with everything else unchanged.",
                     "For example, {phrase} by 20% would change the year-end balance from {base} to {better}.",
                     "It shows which way to push each choice."),
    "company_balance": ("Your running balance month by month, with the likely range.",
                        "{story}",
                        "Below the zero line, your programme has cost more than it has returned so far."),
    "company_donut": ("How your total cost splits by type.",
                      "{biggest} is the largest part: {share} of your total.",
                      "The largest part is where any saving would count most."),
}
DIRECTION_VERB = {"up": "rise", "down": "fall", "flat": "stay about the same"}
DIRECTION_WORDS = {"up": "expected to rise by {change}", "down": "expected to fall by {change}",
                   "flat": "expected to stay about the same"}
SPREAD = {"share": "about {pct} either side", "over": "wider than the expected value itself"}
ADJ = {"strong": "strong", "some": "moderate", "little": "weak"}
WIDTH = {"narrow": "narrow", "moderate": "moderate", "wide": "wide", "very wide": "very wide"}
BIAS = {"low": "too low", "high": "too high", "mixed": "sometimes too low, sometimes too high"}
FEEDS = {"eci_wages_quarterly": "Pay levels set what staff and engineers cost, so they drive training and support, "
                                "setup work and the value of the time people save.",
         "ppi_hosting_monthly": "Hosting prices drive the programme's technology running costs.",
         "burst_tokens_total_daily": "AI usage per day scales the programme's AI usage cost.",
         "other": "This trend is background on how people use AI. It is not used in the money results."}
STORY_BALANCE = ("In the expected outlook money is tied up all year: the balance is lowest at {lowest} in month "
                 "{low_month} and ends at {end}.")
STORY_BALANCE_PAYS = "In the expected outlook it pays for itself in month {month} and ends at {end}."
STORY_OTHERS_PAY = " Only the optimistic outlook pays for itself, in month {month}."
STORY_NONE_PAY = " None of the three outlooks pays for itself within {months} months."
STORY_BENEFIT_ABOVE = "The estimated benefit first beats the cost in month {month}."
STORY_BENEFIT_BELOW = "The estimated benefit stays below the cost in every month of this outlook."
STORY_DOTS_PAYS = ("{names} pays for itself within {months} months", "{names} pay for themselves within {months} months")
STORY_DOTS_NONE = ("{names} does not pay for itself within {months} months",
                   "{names} do not pay for themselves within {months} months")
STORY_BARS = "{none} of the futures we looked at do not pay for themselves within {months} months."
STORY_BARS_MODE = " When it does pay back, month {month} is the most common."
STORY_COMPANY_PAYS = "Your programme pays for itself in month {month} and ends at {end}."
STORY_COMPANY_NOT = "Your programme does not pay for itself within {months} months; it ends at {end}."
SIZE_WORDS = ((0.18, "about a sixth the size of"), (0.22, "about a fifth the size of"),
              (0.29, "about a quarter the size of"), (0.38, "about a third the size of"),
              (0.55, "about half the size of"), (0.7, "about two thirds the size of"),
              (0.85, "about three quarters the size of"), (1.0, "nearly as large as"))
CLOSE_NOTE = " {k} approaches were almost equally close."
PCT_ABOVE_BASE = {"above": "{pct} above", "below": "{pct} below"}
HINT = {"outlook": "How much working time AI saves: cautious, expected or optimistic. The cost is the same in all three.",
        "view": "Likely range adds a shaded band where eight in ten of the futures we looked at land.",
        "series": "The seven public records behind the dashboard. Pay and hosting prices feed the costs.",
        "length": "How far ahead to show. You can only go as far as the saved forecast reaches.",
        "donut_view": "3D view turns and lifts slices as you point at them; Flat view shows the same numbers flat.",
        "show_all": "Show every approach we tried, not only the closest ones.",
}
GLOSSARY_BUTTON = "Word guide"
GLOSSARY_MORE = {
    "Estimate": "A careful best guess, here for the benefit. It is not a measured result.",
    "Forecast / What we expect": "Where a trend is likely to go, worked out from how it moved in the past.",
    "Held back": "Real values we hid on purpose, predicted, and then compared with what really happened.",
    "Approach": "A way of predicting the next values from past ones, from a simple repeat to a blend of several.",
    "Trend": "The long-term direction: up, down or flat.",
    "Repeating pattern": "A shape that comes back every day, week or year, such as busier weekdays.",
    "Unusual point": "A value far from what the usual pattern would suggest. Kept in the data, not removed.",
    "Points (level)": "A price or pay level that tracks change over time. Only the change between two levels matters.",
    "Lakh and crore": "1 lakh = 1,00,000. 1 crore = 100 lakh = 1,00,00,000.",
}
INSIGHTS_DATA_TITLE, INSIGHTS_IDEAS_TITLE = "What the data shows", "Ideas to consider"
INSIGHTS_IDEAS_NOTE = "Suggestions based on the results above. They are not results themselves."
IDEA_LEVER = "Start with {lever}: it moves the year-end balance most ({swing} between 20% lower and 20% higher)."
IDEA_TRAINING = "Keep training and support under watch: it is {share} of all spending."
IDEA_CASH = "Plan for cash to be tied up: in the expected outlook up to {peak} is spent before the benefit catches up."
IDEA_LONGER = "Try a longer project length on Try your own numbers (up to 24 months) to see when it could pay back."
TECH_TITLE = "Explore technical details"

# ---- UI v3: headlines that make the point (filled in from the results where they carry a number) ----
HEAD = {
    "overview_no": "At the example figures, the programme does not pay for itself within {months} months",
    "overview_yes": "At the example figures, the programme pays for itself in month {month}",
    "costs_people": "Most of the cost is people, not technology",
    "costs_other": "{line} is the largest cost",
    "timing_some": "Only the {names} pays for itself within {months} months",
    "timing_expected": "In the expected outlook it pays for itself in month {month}",
    "timing_none": "None of the outlooks pays for itself within {months} months",
    "levers_one": "{a} matters most",
    "levers_two": "{a} and {b} matter most",
    "data": "Seven public records, used as they come",
    "forecast": "Where each trend is heading, and how sure we can be",
    "reliable": "How close our earlier predictions came",
    "company": "Put in your own figures",
}
SUB = {
    "costs": "What the money is spent on each month, and how it compares with the estimated benefit.",
    "timing": "Each outlook, then the month it pays for itself across all the futures we looked at.",
    "levers": "How far each choice can move the year-end balance, with everything else held the same.",
}

RATE_NOTE = "Amounts are shown in Indian rupees, converted at the rate of {rate} per US dollar ({source}, {date})."

MISSING = "Some results are not available yet. Please check back once they have been prepared."
ABOUT_TITLE = "About these numbers"
ABOUT = ("The cost side follows public trends in pay and in technology prices, and public records of how much "
         "people use AI tools. The benefit side uses published surveys and a study on how much working time AI "
         "saves; these give a cautious, an expected and an optimistic outlook. The company itself is an example "
         "with made-up figures. What is uncertain: how prices and pay will move, how much time people really "
         "save, and how much of that time turns into value. The benefit is an estimate, never a promise.")
GLOSSARY = {"Running balance": "Benefit minus cost, added up month by month.",
            "Pays for itself": "The first month the running balance is above zero.",
            "Likely range": "Where the result lands in eight out of ten futures we looked at.",
            "Outlook": "A view of how much time AI saves: cautious, expected or optimistic."}

# ---- the visitor's own figures across the site (set on Try your own numbers; gone after Reset or a page refresh) ----
YOURS = {
    "EXAMPLE_PILL": "Your figures",
    "BANNER": ("You are looking at results for the figures you entered on Try your own numbers. Press Reset to "
               "example there, or refresh the page, to see the example company again."),
    "FOOTER_NOTE": "Results for the figures you entered.",
    "HERO_SUB": "Built on public trends in pay, technology prices and AI use, applied to the figures you entered.",
    "WELCOME_NUMBERS_TITLE": "Your company at a glance",
    "OVERVIEW_SUB": ("The four numbers that matter for your company, how the running balance moves over the year, "
                     "and which choices to look at first."),
    "NO_PAYBACK": ("At your figures, the expected outlook does not pay for itself within {months} months. "
                   "The year-end running balance is {balance}."),
    "ABOUT": ABOUT.replace("The company itself is an example with made-up figures.",
                           "The company figures are the ones you entered on Try your own numbers."),
}
HEAD_YOURS = {"overview_no": "At your figures, the programme does not pay for itself within {months} months",
              "overview_yes": "At your figures, the programme pays for itself in month {month}"}
SIDE_YOURS = "Every results page now shows the figures you entered."
SIDE_YOURS_BACK = "Back to the example"
SIDE_YOURS_HELP = "Show the example company again on every page (a page refresh does the same)."

# ---- PDF report of the results (Try your own numbers, next to the table download) ----
PDF_DOWNLOAD = "Download report (PDF)"
PDF_UNAVAILABLE = "The PDF report is not available on this server right now; the table download has the same numbers."
PDF_WORKING = "Preparing the report..."
PDF_TITLE = "Results report"
PDF_FOR = {"yours": "For the figures you entered", "example": "For the example company (made-up figures)"}
PDF_MADE = "Made on {date}. {rate}"
PDF_SECTIONS = {"summary": "Summary", "balance": "Your running balance", "split": "Where the money goes",
                "monthly": "Monthly cost by type", "benefit": "Estimated benefit and cost each month",
                "outlooks": "The three outlooks", "payback": "Month the programme pays for itself",
                "levers": "What matters most", "inputs": "The figures used", "table": "Month by month",
                "notes": "About these numbers"}
PDF_INPUT_COLS = ["Figure", "Unit", "Value"]
PDF_OUTLOOK_NOTE = "Shown for the {outlook}, chosen on the form. The middle line is the typical case; the band holds 8 in 10 futures."
PDF_LEVERS_NOTE = ("How far the year-end balance moves when each choice is 20% lower or 20% higher, everything else "
                   "unchanged (expected outlook).")
PDF_NOTES = ["The benefit is an estimate of the value of time people save, never a promise.",
             "Each result comes from 5,000 possible futures built from public trends in pay, technology prices and "
             "AI use. 'Typical' means the middle of those futures; 'likely range' holds 8 in 10 of them.",
             "The three outlooks differ in how much time AI saves: cautious (a study where AI slowed work down), "
             "expected (the average measured today) and optimistic (the best industry measured)."]
PDF_AXIS = {"month": "Month", "money": "Amount (₹)", "balance": "Running balance (₹)", "share": "Share of futures",
            "change": "Change in year-end balance (₹)"}
PDF_LEGEND = {"typical": "Typical case", "range": "Likely range (8 in 10)", "cost": "Cost", "benefit": "Estimated benefit",
              "lower": "20% lower", "higher": "20% higher"}
