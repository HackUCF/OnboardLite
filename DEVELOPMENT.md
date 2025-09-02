# Development Setup

This guide will help you set up OnboardLite for local development.

## Prerequisites

- Python 3.12 or later
- Git

## Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/HackUCF/OnboardLite.git
   cd OnboardLite
   ```

2. **Set up Python virtual environment**
   ```bash
   python3 -m venv .venv
   echo ".venv/" > ./.git/info/exclude
   source ./.venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   python3 -m pip install -r requirements.txt
   python3 -m pip install -r requirements-dev.txt
   pre-commit install
   ```

4. **Create configuration directory and copy example config**
   ```bash
   mkdir ./config
   cp options-example.yml ./config/options.yml
   ```

## Configuration

### Discord Integration

1. Go to https://discord.com/developers/applications and create an application
2. Under OAuth2, get the client ID and client secret
3. Set the redirect URL to `http://localhost:8000/api/oauth/?redir=_redir`
4. Update your `config/options.yml`:
   ```yaml
   discord:
     client_id: YOUR_CLIENT_ID
     secret: YOUR_CLIENT_SECRET
     redirect_base: http://localhost:8000/api/oauth/?redir=
     enable: false
   ```

### Email Configuration

For local development, disable email:
```yaml
email:
  enable: false
```

### HTTP Configuration

Set the domain for local development:
```yaml
http:
  domain: localhost:8000
```

### JWT Secret

Set a JWT secret (must be a 32-character random string):
```yaml
jwt:
  secret: your-32-character-random-string-here
```

### Database Configuration

For local development, use SQLite:
```yaml
database:
  url: "sqlite:///database/database.db"  # Create database/ directory first
```

Make sure to create the database directory:
```bash
mkdir database
```

## Running the Application

You have several options to run OnboardLite:

### Option 1: Direct Python execution
```bash
python3 -m uvicorn app.main:app --host 0.0.0.0 --reload --port 8000
```

### Option 2: Docker Compose (recommended for development)
```bash
docker compose -f docker-compose-dev.yml watch
```

The application will be available at http://localhost:8000

## Debugging in VS Code

Create `.vscode/launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI",
            "type": "debugpy",
            "justMyCode": true,
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "app.main:app",
                "--reload",
                "--port",
                "8000"
            ]
        }
    ]
}
```

## Code Quality

This project uses several tools to maintain code quality:

- **Ruff**: For code formatting and linting
- **Pre-commit hooks**: Automatically run checks before commits
- **Pytest**: For running tests

Run the following commands to check your code:

```bash
# Format code
ruff format .

# Run linting
ruff check .

# Run tests
pytest

# Run pre-commit hooks manually
pre-commit run --all-files
```

## Project Structure

```
OnboardLite/
├── app/                    # Main application code
│   ├── forms/             # Form definitions (JSON)
│   ├── models/            # Database models
│   ├── routes/            # API routes
│   ├── static/            # Static files
│   ├── templates/         # Jinja2 templates
│   ├── util/              # Utility functions
│   └── main.py            # FastAPI application entry point
├── tests/                 # Test files
├── config/                # Configuration files (not in git)
├── database/              # Local SQLite database (not in git)
└── docs/                  # Documentation
```

## Editing Forms

To edit questions on forms, modify the JSON files in the `forms/` folder. Each JSON file represents a separate page that acts as a discrete form, with each value correlated to a database entry.

OnboardLite uses a file format based on a simplified [Sileo Native Depiction](https://developer.getsileo.app/native-depictions). The schema is rendered by `util/kennelish.py`.

**Important**: Database entries must be defined in `models/user.py` before being called in a form. Data type validation is enforced by Pydantic.

## Development Tips

1. **Environment Variables**: If running under Docker, the `-e` flag should set the env variable, but for local development you need to set it yourself:
   ```bash
   export ENV=development
   ```

2. **Database Changes**: When modifying database models, you may need to create and run Alembic migrations.

3. **Hot Reloading**: When using `--reload` flag with uvicorn, the server will automatically restart when you make changes to the code.

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you've activated your virtual environment and installed all dependencies.

2. **Database Errors**: Ensure the `database/` directory exists and the database URL in your config is correct.

3. **Port Already in Use**: If port 8000 is busy, you can change the port in the uvicorn command or docker-compose file.

4. **Permission Errors**: On some systems, you might need to use `python` instead of `python3`.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the tests and linting
5. Commit your changes with a descriptive message
6. Push to your fork and create a pull request

Please ensure your code follows the project's coding standards and includes appropriate tests.