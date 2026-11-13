# Buddy — Waiting on background work

Step-loaded unit of `agents/buddy/operational.md` (Phase 2: ACT). Read it before
ending a turn, or a delegate's run, while background work of your own runs (an
agent, a command, a session's own agents), and when a report says that an actor
waits on its own background work. Applicability: every mode, wherever an actor
waits.

Intent: work that runs without anyone watching must not stand still unseen. A
wait is a claim about a process. The actor that started the process sees it
first, so it checks before it ends its turn; whoever receives the claim checks
again before relying on it.

**Ending a turn on a wait.** An actor ends a turn while its own background work
runs only with the first of these that the host offers for that work (host
abilities: `architecture-documentation/07-tool-integrations.md` §Delegation
vehicles):
1. a completion notice the host sends to this actor when the work ends, with
   the work checked as running at that moment (the host's state of the agent,
   command or session, or the process itself);
2. a scheduled check the host offers (a wake-up or a monitor), set before the
   turn ends; when it fires and the work still runs, the next one is set the
   same way;
3. neither: the actor waits for the work in the foreground (a call that returns
   when the work ends; where the host limits one call's time, the same call
   repeated in that turn until the work ends counts as one wait). Work that
   cannot be waited for that way is named in the final message with the event
   at which the actor looks again (its next turn, begun by the user or, for a
   session, by its coordinator), so the reader sees that it stands until then.
The turn-end note names the work, how it was checked as running at this turn
end, and where its output lands; that is a verified wait. A delegate (an isolated agent) has no later turn: it does not
return while its own background work runs; it waits for it in the foreground
and returns the result.

**Receiving a wait report.** A report that an actor waits on its own background
work is not a result and not proof that anything runs. Whoever receives it (a
coordinator from a session's turn-end note, a session or Buddy from an agent's
return) checks in the same turn, in this order:
1. the named output exists: the actor whose work it serves collects it and
   continues: the receiver of an agent's return itself; for a session's own
   agent or command, the session, which its coordinator tells in one message
   that the output is there (the coordinator does not carry out the session's
   work; with the host's message cap reached, that message waits for the
   user's next message in its chat);
2. the named work runs: wait for it as §Ending a turn on a wait says;
3. neither: the wait is over and the actor counts as stopped (a session:
   `agents/buddy/coordinating-sessions.md` §Session end; an agent's unfinished
   work is redone or finished by the receiver, keeping what is usable).
A check uses what the receiver can see: the host's state of the work, the
process list, the output and record locations; reading them costs no message.
Work the receiver cannot see either way (a session's own agents, seen from its
coordinator) is not "neither": the receiver accepts a verified wait; for an
unverified one it asks the actor once (a coordinator, about a session's note:
at the second unverified note in a row, as the last paragraph says) to run
the check of §Ending a turn on a wait (a message, counted against the host's
message cap: `agents/buddy/coordinating-sessions.md` §One reading place), and an answer
without that check, or none by the actor's next turn end, counts as neither.
When a delegate returned while its own work ran, the receiver records beside
its persisted return (without one, in its reply) that it did, what the check
found and which result the receiver collected, waited for or redid itself, so
the record does not show that work as the delegate's.

For a session's turn-end notes this paragraph decides when the coordinator
checks and messages: a wait note is verified when it names the work, how the
session checked at that turn end that it runs, and where its output lands; on each one the coordinator reads the output location.
It accepts one unverified wait note; at the second in a row with no return it
checks as above, and a check that finds the work running starts the count again
(intent: one note can end a turn just before its notice arrives; a second with
nothing new means a cycle passed unseen). Per wait it sends a session at most one
check request and one message that the output is there.
