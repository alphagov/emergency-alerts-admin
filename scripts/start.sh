#! /bin/sh

echo "Start script executing for admin.."

function run_admin(){
  cd $ADMIN_DIR;
  . $VENV_ADMIN/bin/activate && flask run -p 6012 --host=0.0.0.0
}

run_admin
