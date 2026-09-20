"""
AV SUITE BACKEND - LOCAL DEVELOPMENT SETUP GUIDE
==================================================

Purpose: Step-by-step guide for developers to set up backend locally
Yeh guide development environment setup ke liye sabhi steps provide karta hai.

Target Audience: Backend developers, DevOps, Team leads
Estimated Setup Time: 30-45 minutes (first time)
Last Updated: 2026-05-18
"""

# ============================================================================
# PREREQUISITES
# ============================================================================

/*
Required Software:
- Git: Version control (https://git-scm.com/download)
- Python: 3.11 or higher (https://www.python.org/downloads)
- PostgreSQL Client: Connect to database (sudo apt-get install postgresql-client)
- Redis (optional): For caching (https://redis.io/download)
- Docker (optional): Container runtime for Supabase (https://www.docker.com/products/docker-desktop)

Accounts:
- GitHub: Repository access (https://github.com/signup)
- Supabase: Database service (https://supabase.com/auth/signup)

Recommended IDE:
- VS Code: https://code.visualstudio.com
- PyCharm: https://www.jetbrains.com/pycharm

System Resources:
- Disk: 5GB free space minimum
- RAM: 2GB minimum (4GB+ recommended)
- Network: Internet connectivity required
*/


# ============================================================================
# STEP 1: CLONE REPOSITORY
# ============================================================================

/*
1. Open terminal/command prompt

2. Clone repository:
   git clone https://github.com/Aarogya-Virohan/av-suite.git

3. Navigate to backend:
   cd av-suite/backend

4. Verify structure:
   ls -la
   
   Should show:
   - app/          (Application code)
   - tests/        (Test suite)
   - alembic/      (Database migrations)
   - .env.example  (Environment template)
   - pyproject.toml (Dependencies)
   - README.md     (Documentation)
*/


# ============================================================================
# STEP 2: CREATE VIRTUAL ENVIRONMENT
# ============================================================================

/*
Virtual environment isolate karta hai dependencies ko project ke liye.

1. Create virtual environment:
   python3 -m venv .venv
   
   Alternative (if python3 not in PATH):
   python -m venv .venv

2. Activate virtual environment:
   
   On macOS/Linux:
   source .venv/bin/activate
   
   On Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   
   On Windows (Command Prompt):
   .venv\Scripts\activate.bat

3. Verify activation (should show .venv in prompt):
   (.venv) $ 
   
   If not, activation failed. Troubleshoot:
   - Check Python is installed: python3 --version
   - Check write permissions in directory
   - Use full path: /usr/bin/python3 -m venv .venv
*/


# ============================================================================
# STEP 3: INSTALL DEPENDENCIES
# ============================================================================

/*
1. Upgrade pip (package manager):
   pip install --upgrade pip

2. Install development dependencies:
   pip install -e ".[dev]"
   
   This installs:
   - FastAPI, Uvicorn (web framework)
   - SQLAlchemy, asyncpg (database)
   - Pydantic (validation)
   - python-jose (JWT tokens)
   - passlib, bcrypt (password hashing)
   - pytest, pytest-asyncio (testing)
   - And more...

3. Verify installation:
   pip list
   
   Should show all packages installed

4. If issues:
   pip install -e . --force-reinstall
*/


# ============================================================================
# STEP 4: SUPABASE SETUP
# ============================================================================

### Create Supabase Project

/*
1. Go to https://supabase.com

2. Sign up / Log in with GitHub

3. Create new project:
   - Click "New Project"
   - Organization: Select or create
   - Name: av-suite-backend
   - Database Password: Strong password (save securely!)
   - Region: Select closest to your location (for latency)
   - Click "Create new project" (wait 2-3 minutes)

4. Project is created, access Dashboard

5. Get Connection String:
   - Go to Database > Connection String
   - Choose "Connection pooler"
   - Select "Session" mode
   - Copy the connection string
   
   Format should be:
   postgresql+asyncpg://postgres.project_id:password@region.pooler.supabase.com:5432/postgres
*/

### Configure Local Environment

/*
1. Copy environment template:
   cp .env.example .env

2. Update .env file with Supabase credentials:
   
   Open .env in editor:
   nano .env
   
   Update values:
   DATABASE_URL=postgresql+asyncpg://postgres.project_id:password@region.pooler.supabase.com:5432/postgres
   SUPABASE_URL=https://project_id.supabase.co
   SUPABASE_KEY=your_anon_key
   
   Generate strong JWT_SECRET_KEY:
   openssl rand -hex 32
   
   Update JWT_SECRET_KEY with generated value

3. Save and verify:
   cat .env
   
   Should show all required environment variables

4. Security:
   .env file automatically in .gitignore (never commit!)
*/


# ============================================================================
# STEP 5: TEST SUPABASE CONNECTION
# ============================================================================

/*
1. Run connection test script:
   python test_supabase_connection.py

2. Expected output (SUCCESS):
   ============================================================
   🧪 Supabase Connection Verification Test
   ============================================================
   Environment: development
   Debug Mode: True
   Testing connection to: postgresql+asyncpg://postgres.project_id@***@***
   🔄 Creating async database engine...
   ✅ Async engine created successfully
   🔄 Attempting to acquire database connection...
   ✅ Session created successfully
   ✅ Query executed successfully: (1,)
   🎉 Supabase connection is working perfectly!
   ============================================================
   ✅ All checks passed! Backend can connect to Supabase

3. If FAILED:
   - Check DATABASE_URL format
   - Verify credentials (password, project_id, region)
   - Ensure internet connectivity
   - Check Supabase service status
*/


# ============================================================================
# STEP 6: DATABASE MIGRATIONS
# ============================================================================

/*
Alembic manages database schema changes.

1. View migration history:
   alembic history

2. Check current version:
   alembic current

3. Apply migrations:
   alembic upgrade head
   
   This creates database tables and schema

4. Verify migrations applied:
   alembic current
   
   Should show latest revision

5. View database (optional):
   - Go to Supabase Dashboard > SQL Editor
   - Should see new tables (users, patients, exercises, etc.)
   - Inspect structure and data

6. Create new migration (for schema changes):
   alembic revision --autogenerate -m "Description of changes"
   
   Edit generated file: alembic/versions/xxxx_description.py
   Then apply: alembic upgrade head
*/


# ============================================================================
# STEP 7: RUN DEVELOPMENT SERVER
# ============================================================================

/*
1. Start development server:
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

   Flags explained:
   --reload: Auto-restart on code changes
   --host: Listen on all interfaces (0.0.0.0)
   --port: Port 8000

2. Expected output:
   INFO:     Application startup complete
   INFO:     Uvicorn running on http://0.0.0.0:8000

3. Access API:
   - API: http://localhost:8000/docs (Swagger UI)
   - ReDoc: http://localhost:8000/redoc
   - Health: http://localhost:8000/health

4. Test endpoints:
   - Go to http://localhost:8000/docs
   - Try "POST /api/v1/auth/register"
   - Enter test data, click "Try it out"
   - Should get 201 status with access token

5. Stop server:
   Press Ctrl+C (or Cmd+C on macOS)
   pkill if uvicorn || true
*/


# ============================================================================
# STEP 8: RUN TESTS
# ============================================================================

/*
1. Run all tests:
   pytest tests/ -v

2. Expected output:
   collected 1 item
   tests/test_clinic_isolation.py::test_clinic_isolation PASSED [100%]
   ========================== 1 passed in XX.XXs ===========================

3. Run specific test:
   pytest tests/test_clinic_isolation.py -v

4. Run with coverage:
   pip install pytest-cov
   pytest tests/ --cov=app --cov-report=html

5. View coverage report:
   open htmlcov/index.html

6. Run tests in watch mode:
   pytest-watch tests/
*/


# ============================================================================
# STEP 9: IDE SETUP (OPTIONAL)
# ============================================================================

### VS Code Setup

/*
1. Install extensions:
   - Python (ms-python.python)
   - Pylance (ms-python.vscode-pylance)
   - FastAPI extension (optional)

2. Configure Python interpreter:
   - Open command palette: Ctrl+Shift+P
   - Type "Python: Select Interpreter"
   - Choose "./.venv/bin/python"

3. Run and Debug:
   - Click "Run" > "Add Configuration"
   - Select "Python"
   - Create launch.json with:
   {
       "version": "0.2.0",
       "configurations": [
           {
               "name": "FastAPI",
               "type": "python",
               "request": "launch",
               "module": "uvicorn",
               "args": ["app.main:app", "--reload"],
               "console": "integratedTerminal"
           }
       ]
   }

4. Press F5 to start debugging

5. Set breakpoints:
   - Click line number to set breakpoint
   - Variables inspector on left
*/

### PyCharm Setup

/*
1. Open backend directory as project

2. Configure interpreter:
   - File > Settings > Project > Python Interpreter
   - Add > Existing Environment > .venv/bin/python

3. Configure run configuration:
   - Run > Edit Configurations
   - Add new > Python
   - Module: uvicorn
   - Parameters: app.main:app --reload
   - Click OK

4. Run project:
   - Click green play button
   - Or press Shift+F10

5. Debugging:
   - Click in gutter to set breakpoint
   - Click debug (bug icon)
   - Step through code
*/


# ============================================================================
# DEVELOPMENT WORKFLOW
# ============================================================================

/*
Daily development workflow:

1. Activate virtual environment:
   source .venv/bin/activate

2. Pull latest changes:
   git pull origin main

3. Start development server:
   uvicorn app.main:app --reload

4. In another terminal:
   pytest tests/ -v

5. Write code:
   - Edit app files
   - Server auto-reloads
   - Tests auto-run

6. When done:
   git add .
   git commit -m "Feature: Description"
   git push origin main

7. Create Pull Request on GitHub

8. After merge:
   git checkout main
   git pull origin main
*/


# ============================================================================
# COMMON DEVELOPMENT TASKS
# ============================================================================

### Add New Endpoint

/*
1. Create endpoint file: app/api/v1/new_feature.py

2. Create route:
   @router.get("/endpoint")
   async def new_endpoint(request: Request, db: AsyncSession = Depends(get_db)):
       # Logic here
       return {"data": "response"}

3. Register in router: app/api/v1/router.py

4. Test in Swagger UI: http://localhost:8000/docs

5. Add tests: tests/test_new_feature.py
*/

### Add New Database Model

/*
1. Create model: app/models/new_model.py

2. Create migration:
   alembic revision --autogenerate -m "Add new_model table"

3. Verify migration file: alembic/versions/xxxx_add_new_model.py

4. Apply migration:
   alembic upgrade head

5. Update services: app/services/new_model_service.py

6. Create API endpoints: app/api/v1/new_model.py

7. Add tests
*/

### Add New Dependency

/*
1. Install package:
   pip install package-name

2. Add to pyproject.toml: dependencies section

3. Update everyone:
   git add pyproject.toml
   git commit -m "Add dependency: package-name"
   git push origin branch-name

4. Others update locally:
   pip install -e .
*/

### Database Debugging

/*
1. Access database directly:
   - Go to Supabase Dashboard
   - Click SQL Editor
   - Run queries

2. View migrations:
   alembic history

3. Rollback migration:
   alembic downgrade -1

4. Check current state:
   alembic current

5. View all tables:
   SELECT tablename FROM pg_tables WHERE schemaname='public';
*/


# ============================================================================
# TROUBLESHOOTING
# ============================================================================

### Python Not Found

/*
Solution:
python3 --version
/usr/bin/python3 -m venv .venv
*/

### Virtual Environment Not Activating

/*
Solution:
source .venv/bin/activate
# Or full path:
source /full/path/to/project/.venv/bin/activate
*/

### Database Connection Failed

/*
Solution:
1. Verify .env has DATABASE_URL
2. Run test_supabase_connection.py
3. Check credentials in Supabase dashboard
4. Verify internet connectivity
5. Check Supabase service status
*/

### Tests Failing

/*
Solution:
1. Check if database connected: python test_supabase_connection.py
2. Apply migrations: alembic upgrade head
3. Run single test: pytest tests/test_specific.py -v
4. View error details: pytest tests/ -v --tb=short
*/

### Port 8000 Already in Use

/*
Solution:
# Option 1: Use different port
uvicorn app.main:app --port 8001

# Option 2: Kill process using port
lsof -i :8000
kill -9 <PID>
*/

### Module Not Found Error

/*
Solution:
pip install -e .
pip install --force-reinstall -e .
*/


# ============================================================================
# BEST PRACTICES
# ============================================================================

✓ Always work in virtual environment
✓ Keep dependencies updated: pip install --upgrade -e .
✓ Run tests before pushing: pytest tests/
✓ Follow code style: PEP 8
✓ Write meaningful commit messages
✓ Comment complex logic in Hinglish
✓ Test your changes thoroughly
✓ Don't commit .env file
✓ Use git branches for features
✓ Create pull requests for review
✓ Keep database migrations separate
✓ Document new features/endpoints


# ============================================================================
# USEFUL COMMANDS REFERENCE
# ============================================================================

# Activate environment
source .venv/bin/activate

# Deactivate environment
deactivate

# Install/upgrade dependencies
pip install -e .
pip install --upgrade -e .

# Start development server
uvicorn app.main:app --reload

# Run tests
pytest tests/ -v

# Database migrations
alembic upgrade head
alembic downgrade -1
alembic history

# Git commands
git status
git add .
git commit -m "message"
git push origin branch-name

# Clean up
rm -rf .pytest_cache
rm -rf __pycache__
find . -type d -name __pycache__ -exec rm -r {} +


# ============================================================================
# NEXT STEPS
# ============================================================================

1. ✓ Complete this setup
2. ✓ Run development server successfully
3. ✓ Access http://localhost:8000/docs
4. ✓ Test endpoints with sample data
5. ✓ Run test suite (pytest)
6. ✓ Read API_DOCUMENTATION.md
7. ✓ Explore codebase structure
8. ✓ Start implementing features

Questions or issues? 
- Check existing documentation
- Review code comments in Hinglish
- Ask team members
- Check GitHub issues


# ============================================================================
# SUPPORT RESOURCES
# ============================================================================

Documentation:
- API_DOCUMENTATION.md - API endpoints reference
- DEPLOYMENT_GUIDE.md - Production deployment
- SUPABASE_SETUP_GUIDE.md - Supabase configuration
- EXECUTION_GUIDE.md - Development guidelines
- PROGRESS_REPORT.md - Project status

External Resources:
- FastAPI: https://fastapi.tiangolo.com
- SQLAlchemy: https://www.sqlalchemy.org
- Pydantic: https://docs.pydantic.dev
- Supabase: https://supabase.com/docs
- PostgreSQL: https://www.postgresql.org/docs

Team:
- GitHub: https://github.com/Aarogya-Virohan/av-suite
- Issues: Report bugs on GitHub
- Discussions: Share ideas and questions
"""
