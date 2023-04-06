#! /bin/sh

echo "Start script executing for admin.."

function configure_container_role(){
  aws configure set default.region eu-west-2
}

function run_admin(){
  cd $ADMIN_DIR;
  . $VENV_ADMIN/bin/activate && flask run -p 6012 --host=0.0.0.0
}

configure_container_role
run_admin
