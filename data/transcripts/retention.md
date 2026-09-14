# Retention and the Real Cost of a Leaky Bucket

**Guest:** Tomas Reyes, Retention lead at a consumer subscription app

Lenny: There's a popular saying that retention is more important than acquisition. Do you agree, and why doesn't everyone act like it's true?

Tomas: I agree completely, and the reason nobody acts on it is that acquisition results show up in a week and retention results show up in a quarter. A leaky bucket means every dollar of acquisition spend is partially wasted refilling water that's draining out the bottom. If your monthly churn is 8%, you're effectively replacing your entire customer base every year just to stay flat, and that math gets brutal at scale — growth teams that ignore this end up on a acquisition treadmill that never gets easier, no matter how much budget increases.

Lenny: How do you separate churn that's fixable from churn that's just natural attrition?

Tomas: I segment churn into three buckets: involuntary churn from failed payments, which is almost entirely fixable with better dunning and card-retry logic; voluntary churn from users who got value and moved on because their need ended, which is mostly not fixable and shouldn't be chased; and voluntary churn from users who never really got value, which is the bucket worth obsessing over because it's a product problem you can actually solve. Lumping all three into one "churn rate" number hides where the real leverage is.

Lenny: What's an underrated lever for improving retention that isn't "build more features"?

Tomas: Re-engagement timing. Most churn doesn't happen the day someone decides to quit — it happens weeks earlier when they quietly stop opening the app, and the actual cancellation is just the final paperwork. If you can detect the early silence — say, seven days of no opens for a product people used daily — and intervene with something genuinely useful, not just a generic "we miss you" email, you can win back a meaningful chunk of users before they've mentally checked out.

Lenny: How do you think about the difference between retention and engagement?

Tomas: Engagement is necessary but not sufficient. You can have a user opening your app every day out of habit while getting decreasing value, and that's a ticking time bomb, not a healthy metric. I look for engagement paired with an outcome — not "opened the app" but "completed the workout" or "finished the lesson." A product can have great daily-open numbers and be one bad month away from a churn cliff if the engagement isn't tied to real value delivery.

Lenny: Cohort retention curves — how do you read one properly?

Tomas: The shape matters more than any single number. A curve that keeps declining slowly forever means you haven't found your core retained audience — you're just churning slower. A curve that declines and then flattens, even at a lower percentage, means you've found a group who will stick around indefinitely, and your job becomes growing the size of that flat group, not just slowing the initial decline. I've seen teams celebrate a flatter early slope while missing that the curve never actually levels off, which is a much worse sign long-term.

Lenny: What would you tell a founder who says "we'll fix retention once we're bigger"?

Tomas: I'd tell them retention problems don't fix themselves with scale — they get amplified by it. A leaky product at 1,000 users is a leaky product at 100,000 users, except now the absolute number of frustrated churned customers is loud enough to become a reputation problem. Fix the leak first; acquisition should be the thing you turn up once you know the water is staying in the bucket, not a way to distract from the leak.
