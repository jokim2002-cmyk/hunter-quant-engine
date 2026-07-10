# HQE App V2 Single Instance and Watch Guard V1

- A Windows named mutex prevents a second HQE App V2 GUI instance.
- Status and guard CLI modes remain available without the GUI mutex.
- Start Paper Watch checks all actual Windows Python processes first.
- An existing global paper watch returns its canonical PID instead of launching a duplicate.
- Existing paper-only safety locks remain unchanged.
