# AI Usage Reflection

*As requested: honesty here matters more than the answer itself.*

## 1. What did you use AI for across the four sections?

- **Section 1 (System Design):** I created the initial system design myself — deciding on the models, the API endpoints, and the shift/working-hours feature. My first prompt to the AI in this project was essentially my own breakdown of the system (the models I wanted, the endpoints, the shift concept), and that breakdown is my version of the system design. From there, AI helped refine specific pieces of it: the split between `Slot` and `Appointment` as separate models, the `unique_together` + `select_for_update()` approach to preventing double-booking, and where the 1-hour-buffer/past-slot logic should live (a shared queryset method vs. duplicated checks).
- **Section 2 (API Implementation):** AI helped in three main ways — autocomplete-style code suggestions in the editor, debugging issues and filling in gaps while writing code, and generating the management command that auto-generates slots.
- **Section 3 (Deployment & CI/CD):** Writing the GitHub Actions workflow, the Dockerfile-compatible `start.sh` entrypoint, and — heavily — debugging a long chain of real deployment failures (Windows line-ending issues, Render's Docker Command field not behaving like a normal shell, missing dependencies, mismatched environment variable names, a wrong Postgres hostname used as a database name).
- **Section 4 (this reflection):** AI helped refine this document.

## 2. Give one example where an AI suggestion improved your work. What did you prompt it with?

When designing the appointment-booking logic, I asked how to prevent two patients from booking the same slot simultaneously. The AI suggested wrapping the slot-state change in `transaction.atomic()` combined with `Slot.objects.select_for_update()` inside the booking view, rather than just checking `is_booked` and then setting it in two separate steps. This closes an actual race condition: without the row lock, two near-simultaneous requests could both pass the "is this booked?" check before either had written `is_booked=True`, resulting in two appointments for one slot. I hadn't been aware of `select_for_update()` before this, and reused the same pattern later for the reschedule endpoint.

## 3. Give one example where AI output was wrong or incomplete and how you caught it.

While setting up the Render deployment, the Docker Command kept failing to run a chained shell command (`collectstatic && migrate && gunicorn ...`). The AI's first fix was to wrap the whole command in `sh -c "..."`, reasoning that Render must not be passing the command through a shell. That produced a *different* error (`sh: 1: <entire command string>: not found`), which actually indicated the opposite problem — the command was being wrapped in a shell twice, not zero times. Rather than accept a second guess, I asked the AI to actually verify how Render's Docker Command field works rather than keep guessing, and it searched Render's own community forum, found other users hitting the identical issue, and confirmed the field doesn't reliably support inline command chaining at all. The real fix was moving the command sequence into a committed `start.sh` script instead. I caught the initial wrong assumption by noticing the *second* error message contradicted the theory behind the *first* fix, rather than assuming the second attempt was automatically closer to correct.

## 4. Name two decisions you made without AI. Why did you trust your own judgment there?

1. **The system design.** I decided on the models, the API endpoints, and the shift/working-hours feature myself before involving AI at all. AI's role was limited to helping address specific gaps in that design (e.g. race-safety mechanics) — the overall shape of the system was mine.
2. **The GitHub branching strategy.** I decided how the branches should be structured (accounts, appointments-core, ci-cd-deployment, and so on) and how work should be sequenced across them. This was my own judgment about how to organize the project's history, not something AI proposed.
3. **The scaffolding for models, serializers, views, and URL wiring.** I made the actual structural decisions here; AI's contribution was filling in gaps in the code once the structure was set, not deciding the structure itself.
4. **The tech stack decision** — choosing Django, Docker, GitHub, and Render for deployment. These were my own choices going into the project, based on what I wanted to build with and deploy to, rather than an AI-suggested stack.
