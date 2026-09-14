# Onboarding Design Principles That Actually Convert

**Guest:** Felix Amaro, Head of Design at a project management SaaS company

Lenny: Onboarding advice online is mostly "reduce friction." Is that actually the right frame?

Felix: It's incomplete. Reducing friction matters, but the deeper principle is matching the onboarding path to user intent. Someone who arrived from a specific "how to build a Gantt chart" search article wants to build a Gantt chart in the next sixty seconds — showing them a generic five-step product tour is friction, even though the tour itself is short. The lowest-friction path is the one that gets each user to their specific goal, not the shortest path in absolute steps.

Lenny: How do you figure out what "specific goal" a new user actually has when they land?

Felix: Ask, don't assume — but ask cheaply. A single-question, low-commitment prompt like "what are you hoping to do today?" with three or four concrete options gets you enough signal to branch the experience without feeling like a form. We saw a 22% lift in week-one retention just from branching the first-run experience based on that one question, because a "I'm managing a team project" user and a "I'm tracking my personal tasks" user were being shown the exact same template before that.

Lenny: What's your take on progress bars and checklists in onboarding?

Felix: They work when the steps in the checklist are genuinely valuable on their own, and they backfire when they're just there to be checked off. If step three of your checklist is "invite a teammate" but the product hasn't yet proven its value to the first user, you're asking them to vouch for something they don't believe in yet. Order matters: prove value first, then ask for the actions that require social risk, like inviting someone else.

Lenny: Empty states get overlooked a lot. What do you do differently there?

Felix: An empty state is a decision point, not a placeholder. Instead of "you have no projects yet," we show a pre-populated sample project the user can immediately explore and delete, because manipulating something real teaches the interface faster than reading instructions about a blank screen. The mistake is treating the empty state as an afterthought when it's often the very first meaningful screen a user interacts with after signup.

Lenny: How do you balance teaching the product versus just getting out of the way?

Felix: I default to getting out of the way and only teach exactly when a user is stuck, not preemptively. Contextual tooltips that fire the second time a user hovers near a feature without using it beat a scripted tour that fires for everyone regardless of whether they need it. Scripted tours teach confident users things they already inferred and still fail to help genuinely confused users who clicked past it.

Lenny: If a team can only fix one onboarding problem this quarter, how do you help them choose?

Felix: Look at the step in your onboarding funnel with the single largest drop-off, not the step people complain about most in interviews — those are often different steps, because the biggest drop-off is frequently silent abandonment nobody complains about because they just left. Fix the biggest quantitative leak first; the qualitative complaints are usually about a step people care enough to still be using, which is a good problem to have compared to silent churn.
