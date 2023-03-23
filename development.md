# Installation & Development

**Install Python**
Download python3.11

**Create virtualenv**
```bash
python3.11 -m venv .venv
```

**Use virtualenv**
```bash
source .venv/bin/activate
```

**Apply requirements.txt**
```bash
python3.11 -m pip install -r requirements.txt
```

**Run server**
```python
kopf run --standalone --liveness=http://0.0.0.0:8080/healthz handlers.py
```

----- 