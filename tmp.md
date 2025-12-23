# Complete Step-by-Step Internals of asyncio

Let me break this down with a concrete example, showing exactly what happens at each step.

## The Example Code

```python
import asyncio

async def fetch_data():
    print("Fetching data...")
    await asyncio.sleep(1)
    print("Data fetched!")
    return "result"

async def main():
    print("Starting main")
    result = await fetch_data()
    print(f"Got: {result}")

asyncio.run(main())
```

## Step-by-Step Execution

### **Step 1: `asyncio.run(main())` is called**

**What happens:**

- Python creates a **new event loop** (think of it as a scheduler/manager)
- The event loop is essentially a `while True` loop that:
    - Keeps a list of tasks ready to run
    - Monitors I/O operations (network, files, timers)
    - Decides which task to execute next

**Internal state:**

```
Event Loop:
  - ready_queue: []  (tasks ready to run)
  - scheduled_tasks: []  (tasks waiting for timers)
  - io_waiters: {}  (tasks waiting for I/O)
```

---

### **Step 2: `main()` is called**

**What happens:**

- `main()` is an `async def` function
- Calling it does **NOT** execute the function body
- Instead, it returns a **coroutine object**

**Think of a coroutine as:**

- A frozen function with a "pause button"
- It has an internal instruction pointer saying "start here"
- It implements the iterator protocol (`__await__`, `send()`, `throw()`)

**Internal state:**

```
coroutine object <main>:
  - code: the function body
  - instruction_pointer: line 1 (print("Starting main"))
  - state: CREATED
  - stack: empty
```

---

### **Step 3: Event loop wraps the coroutine in a Task**

**What happens:**

- The event loop creates a `Task` object
- `Task` is a wrapper that:
    - Holds the coroutine
    - Knows how to drive it forward
    - Tracks its state (PENDING → RUNNING → DONE)
    - Can store a result or exception

**Internal state:**

```
Task <main>:
  - coroutine: <coroutine object main>
  - state: PENDING
  - result: None
  - callbacks: []

Event Loop:
  - ready_queue: [Task <main>]
```

---

### **Step 4: Event loop starts - First iteration**

**What happens:**

- Event loop picks `Task <main>` from the ready queue
- It calls `Task._step()` internally, which does:
    
```python
# Simplified pseudocode
  def _step(self):
      try:
          # Resume the coroutine
          awaitable = self.coroutine.send(None)
      except StopIteration as e:
          # Coroutine finished
          self.result = e.value
          self.state = DONE
```
    

**Coroutine executes:**

```python
print("Starting main")  # ✓ Executes
result = await fetch_data()  # ← Pauses here
```

**What `await fetch_data()` does:**

1. Calls `fetch_data()` → returns a coroutine object
2. The `await` tells Python: "pause here, wait for this coroutine to finish"
3. The coroutine **yields** this awaitable back to the Task

**Internal state:**

```
Task <main>:
  - state: WAITING
  - waiting_on: <coroutine object fetch_data>

Event Loop creates a new Task for fetch_data:

Task <fetch_data>:
  - coroutine: <coroutine object fetch_data>
  - state: PENDING
  
Task <main> registers a callback:
  "When Task <fetch_data> is done, resume me"

Event Loop:
  - ready_queue: [Task <fetch_data>]
```

**Output so far:**

```
Starting main
```

---

### **Step 5: Event loop - Second iteration**

**What happens:**

- Event loop picks `Task <fetch_data>` from the ready queue
- Calls `Task._step()` on it

**Coroutine executes:**

```python
print("Fetching data...")  # ✓ Executes
await asyncio.sleep(1)  # ← Pauses here
```

**What `await asyncio.sleep(1)` does:**

1. `asyncio.sleep(1)` creates a **Future** object (a promise for a future result)
2. The Future registers a timer with the event loop: "call me in 1 second"
3. The coroutine yields this Future back to the Task

**Internal state:**

```
Future <sleep>:
  - state: PENDING
  - scheduled_time: current_time + 1 second

Task <fetch_data>:
  - state: WAITING
  - waiting_on: Future <sleep>

Task <fetch_data> registers a callback on the Future:
  "When this timer fires, resume me"

Event Loop:
  - ready_queue: []  (empty!)
  - scheduled_tasks: [Future <sleep> at time T+1]
```

**Output so far:**

```
Starting main
Fetching data...
```

---

### **Step 6: Event loop - Idle waiting**

**What happens:**

- Event loop checks: "Any tasks ready? No."
- Event loop checks: "Any timers about to fire? Yes, in 1 second."
- Event loop **sleeps** for 1 second (using OS-level sleep)
- This is efficient - not a busy-wait loop

**Internal state:**

```
Event Loop: sleeping, waiting for timer...
```

---

### **Step 7: Timer fires (1 second later)**

**What happens:**

- OS wakes up the event loop
- Event loop sees the timer for `Future <sleep>` has expired
- It marks the Future as DONE
- The Future's callback is triggered, which adds `Task <fetch_data>` back to the ready queue

**Internal state:**

```
Future <sleep>:
  - state: DONE
  - result: None

Event Loop:
  - ready_queue: [Task <fetch_data>]
```

---

### **Step 8: Event loop - Third iteration**

**What happens:**

- Event loop picks `Task <fetch_data>` from ready queue
- Calls `Task._step()` which resumes the coroutine
- The coroutine continues from exactly where it paused

**Coroutine executes:**

```python
await asyncio.sleep(1)  # ← Resumes here, gets None result
print("Data fetched!")  # ✓ Executes
return "result"  # ← Coroutine finishes
```

**What happens on `return`:**

- The coroutine raises `StopIteration("result")`
- The Task catches this and:
    - Sets its result to `"result"`
    - Marks itself as DONE
    - Calls its done callbacks

**Internal state:**

```
Task <fetch_data>:
  - state: DONE
  - result: "result"

This triggers the callback registered by Task <main>!

Event Loop:
  - ready_queue: [Task <main>]
```

**Output so far:**

```
Starting main
Fetching data...
Data fetched!
```

---

### **Step 9: Event loop - Fourth iteration**

**What happens:**

- Event loop picks `Task <main>` from ready queue
- Resumes the coroutine from where it paused

**Coroutine executes:**

```python
result = await fetch_data()  # ← Resumes here, gets "result"
print(f"Got: {result}")  # ✓ Executes
# Function ends (implicit return None)
```

**What happens on completion:**
```

- Task <main> marks itself as DONE
- Event loop sees no more tasks
- `asyncio.run()` returns the result
```
**Output:**

```
Starting main
Fetching data...
Data fetched!
Got: result
```

---

## Visual Timeline

```
Time →

[Event Loop Created]
    │
    ├─ Create Task <main>
    │
    ▼
[Iteration 1] Run Task <main>
    │  └─ Print "Starting main"
    │  └─ await fetch_data() → PAUSE
    │       └─ Create Task <fetch_data>
    │
    ▼
[Iteration 2] Run Task <fetch_data>
    │  └─ Print "Fetching data..."
    │  └─ await sleep(1) → PAUSE
    │       └─ Schedule timer
    │
    ▼
[Sleep 1 second]
    │
    ▼
[Timer fires] Future <sleep> DONE
    │
    ▼
[Iteration 3] Resume Task <fetch_data>
    │  └─ Print "Data fetched!"
    │  └─ return "result" → Task DONE
    │       └─ Trigger callback → Resume Task <main>
    │
    ▼
[Iteration 4] Resume Task <main>
    │  └─ Get result "result"
    │  └─ Print "Got: result"
    │  └─ Task DONE
    │
    ▼
[Event Loop Exits]
```

---

## Key Objects Explained

### **1. Coroutine**

- A paused function created by `async def`
- Has an instruction pointer (like a bookmark)
- Can be resumed with `.send(value)`
- Yields awaitables when it hits `await`

### **2. Task**

- Wrapper around a coroutine
- Drives the coroutine forward
- Registers callbacks on awaitables
- Tracks state: PENDING → RUNNING → DONE

### **3. Future**

- A placeholder for a value that will be available later
- Used for I/O operations, timers, etc.
- Has callbacks that fire when it completes

### **4. Event Loop**

- The scheduler/orchestrator
- Maintains queues of ready tasks
- Monitors timers and I/O
- Decides what to run next

### **5. Awaitable**

- Anything you can `await`
- Must implement `__await__()`
- Examples: coroutine, Task, Future

---

## The Magic of `await`

When you write:

```python
result = await something
```

What actually happens:

1. The coroutine **yields** the awaitable to its Task
2. Control returns to the event loop
3. The Task registers a callback: "resume me when this completes"
4. The event loop schedules the awaitable
5. When done, the callback fires
6. The Task resumes the coroutine
7. The coroutine continues from the `await` line

This is why async code is non-blocking - the coroutine pauses, freeing the event loop to do other work.

---

