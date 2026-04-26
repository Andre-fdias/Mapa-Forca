#!/bin/bash
set -e

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running migrations..."
python manage.py migrate

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Creating superuser if needed..."
python create_admin.py

echo "Syncing data from Google Sheets..."
python manage.py sync_viaturas_sheets || echo "Falha ao sincronizar viaturas"
python manage.py sync_postos_sheets || echo "Falha ao sincronizar postos"
python manage.py sync_efetivo_sheets || echo "Falha ao sincronizar efetivo"

echo "Build completed successfully!"
