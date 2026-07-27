#! /bin/sh

echo "Start script executing for admin.."

function configure_container_role(){
    aws configure set default.region ${AWS_REGION:-eu-west-2}
}

PYTHON_COMMAND="python -m"
if [[ ! -z $DEBUGPY_PORT ]]; then
    echo "Starting with debugpy on port $DEBUGPY_PORT"
    PYTHON_COMMAND="python -Xfrozen_modules=off -m debugpy --listen 0.0.0.0:${DEBUGPY_PORT} -m"
fi

function run_admin(){
    cd $DIR_ADMIN;
    . $VENV_ADMIN/bin/activate && exec opentelemetry-instrument $PYTHON_COMMAND flask run -p 6012 --host=0.0.0.0
}

if [[ ! -z $DEBUG ]]; then
    echo "Starting in debug mode.."
    while true; do echo 'Debug mode active..'; sleep 30; done
else
    configure_container_role
    run_admin
fi
