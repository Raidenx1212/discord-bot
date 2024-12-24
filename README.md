
# Discord Bot

A Python-based Discord bot designed to simplify interactions and provide enhanced functionalities for your server.

## Features

- **Automated Responses:** Handles custom commands to interact with users.
- **MongoDB Integration:** Efficient database management for storing server or user data.
- **Extensibility:** Easy to add new features or commands.
- **Environment Variables:** Securely manage sensitive information like API keys.

## Installation

Follow these steps to set up and run the bot:

1. **Clone the Repository:**  
   ```bash
   git clone https://github.com/Raidenx1212/discord-bot.git
   cd discord-bot
   ```

2. **Set Up Virtual Environment:**  
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies:**  
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**  
   Create a `.env` file in the root directory with the following variables:
   ```env
   DISCORD_TOKEN=your-discord-bot-token
   MONGO_URI=your-mongodb-uri
   ```

5. **Run the Bot:**  
   ```bash
   python bot3.py
   ```

## Files Overview

- `bot3.py`: The main bot script containing the core functionalities.
- `test_db.py`: A script to test MongoDB connections.
- `requirements.txt`: Lists all Python dependencies.
- `.env`: Stores environment variables securely (not shared publicly).
- `venv`: Virtual environment directory (not included in the repository).

## Contributing

Contributions are welcome! Feel free to submit a pull request or open an issue for suggestions and improvements.



### Author

Developed by **Raidenx1212**.  
Feel free to reach out or contribute to make this bot even better!
