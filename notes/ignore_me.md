<!-- These are my personal notes. You can ignore this. -->
#### These are my personal notes. You can ignore this.
```bash
sudo -u postgres psql -c "CREATE DATABASE axiomos OWNER axiomos_user;" \
&& source .venv/bin/activate \
&& python -c "from src.database import db_manager; db_manager.create_tables(); print('Database tables created successfully')"
```