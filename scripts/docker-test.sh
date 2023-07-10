#! /bin/sh

function get_account_number(){
  id=$(aws sts get-caller-identity)
  ECS_ACCOUNT_NUMBER=$(echo $id | jq -j .Account)
  if [[ -z $ECS_ACCOUNT_NUMBER ]]; then
    echo "Unable to find AWS account number"
    exit 1;
  fi
}

function ecr_login(){
  aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECS_ACCOUNT_NUMBER.dkr.ecr.$REGION.amazonaws.com
}

function docker_build(){
  docker build \
    -t $ECS_ACCOUNT_NUMBER.dkr.ecr.$REGION.amazonaws.com/eas-app-$IMAGE:latest \
    -f Dockerfile.eas-$IMAGE \
    --no-cache \
    .
}

function docker_test(){
  echo "do something here"
}

get_account_number
ecr_login
docker_build
docker_test
