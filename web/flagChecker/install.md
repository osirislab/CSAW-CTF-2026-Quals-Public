# Setup

1. Create and activate a virtual environment:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set the flag in `.env`:
   ```
   FLAG=csaw{...}
   ```

4. Run the server:
   ```
   python app.py
   ```

The server listens on `0.0.0.0:5000` by default.
