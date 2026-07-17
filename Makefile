# Thin orchestration layer over scripts/ (no build deps required).
# Each target just calls the corresponding self-validating script.

.PHONY: test build verify publish install-web

test:        ./scripts/test.sh
build:       ./scripts/build.sh
verify:      ./scripts/verify_package.sh
publish:     ./scripts/publish.sh
install-web: ./scripts/install_web.sh
