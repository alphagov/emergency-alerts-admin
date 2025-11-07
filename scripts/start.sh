#! /bin/sh

echo "Start script executing for admin.."

function configure_container_role(){
    aws configure set default.region ${AWS_REGION:-eu-west-2}
}

function run_admin(){
    cd $DIR_ADMIN;
    . $VENV_ADMIN/bin/activate && OTEL_PYTHON_DISTRO="aws_distro" OTEL_PYTHON_CONFIGURATOR="aws_configurator" opentelemetry-instrument flask run -p 6012 --host=0.0.0.0
}

if [[ ! -z $DEBUG ]]; then
    echo "Starting in debug mode.."
    while true; do echo 'Debug mode active..'; sleep 30; done
else
    configure_container_role
    run_admin
fi
