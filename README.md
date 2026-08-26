Architecture

API responsibility
- Validates and accepts a HTTP req.
- Creates the jon

worker responsibility
- complete the job, if failure, retry, and go throguh worker lifecycle
- Find the qued job and execute with persistence

database responsibility
- Maintain persistence and ensure workers are not suddenly interupted, has the "durable truth"
- Details of the job, in case worker or API failure, essentially instructions

definition of a job
- Anything a worker can execute, like recording resizing a image while the ui shows a loading screen
- Some durable unit of work, will eventually be executed by worker

initial states
- Not sure
- queued → running → succeeded, failed counts as intiial fauilure state (different states)

initial job types
- Not sure
- simulate_work, sum-work, process_csv, generate_report

happy-path sequence
- client submits job → API validates → API persists job as queued → API returns job information/status → worker later finds/receives job → worker marks it running → worker executes it→ worker stores result → job becomes succeeded → client later asks API for status/result
