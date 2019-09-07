###################################
.DEFAULT_GOAL := default
###################################
.PHONY: default
default: plan

.PHONY:
prep:
	mkdir -p logs

.PHONY:
init:
	rm -rfv .terraform
	terraform init

.PHONY:
plan: prep
	terraform plan -no-color 2>&1 | tee logs/plan.out

.PHONY:
apply: prep
	terraform apply 2>&1 | tee logs/apply.out

.PHONY:
show: prep
	terraform show -no-color 2>&1 | tee logs/show.out

.PHONY:
output: prep
	terraform output | tee logs/output.out

.PHONY:
clean:
	find logs/ -type f -delete

.PHONY:
cleanall: clean
	rm -rfv .terraform
	rm -fv *tfstate*
