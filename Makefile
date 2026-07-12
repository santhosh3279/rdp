VERSION := $(shell cat VERSION)
DIRNAME := $(notdir $(CURDIR))

install:
	sudo bash deploy/install.sh

# Upgrading IS reinstalling: unpack the new version over this directory
# (or git pull) and run make upgrade. Configs and live sessions survive.
upgrade: install

uninstall:
	sudo bash deploy/uninstall.sh

purge:
	sudo bash deploy/uninstall.sh --purge

package:
	tar --exclude-vcs --exclude='*.tar.gz' --exclude='__pycache__' \
	    -czf kiosk-admin-$(VERSION).tar.gz -C .. $(DIRNAME)
	@echo "built kiosk-admin-$(VERSION).tar.gz"

# Regenerate docs/kiosk-admin-guide.pdf after editing docs/guide.html
pdf:
	wkhtmltopdf --enable-local-file-access \
	    --margin-top 18mm --margin-bottom 18mm \
	    --margin-left 16mm --margin-right 16mm \
	    --footer-center '[page] / [topage]' --footer-font-size 8 --footer-spacing 6 \
	    docs/guide.html docs/kiosk-admin-guide.pdf

.PHONY: install upgrade uninstall purge package pdf
