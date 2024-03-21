#! /bin/sh

function check_status_endpoint(){
  curl -f 0.0.0.0:6012/_admin_status || exit 1
}

if [[ $DEBUG == "true" ]]; then
  echo "Debug mode active.."
else
  check_status_endpoint
fi
