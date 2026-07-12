// kiosk profile prefs, copied into each user's profile on every browser start.
// Managed by kiosk-admin: edit /etc/kiosk/firefox-user.js, not the profile copy.

// required for userChrome.css (the tab-strip-only skin) to load
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);

// tabs merge into the titlebar = tab strip sits at the very top of the screen
user_pref("browser.tabs.inTitlebar", 1);

// Ctrl+W on the last tab must not kill the window
user_pref("browser.tabs.closeWindowWithLastTab", false);

// tabs opened from links always append at the END of the strip, never
// between the default tabs -- the generated userChrome.css rule relies on
// the first N positions always being the KIOSK_URLS tabs
user_pref("browser.tabs.insertRelatedAfterCurrent", false);
user_pref("browser.tabs.insertAfterCurrent", false);

// no first-run tour, default-browser nag, or crash-restore prompts
user_pref("browser.aboutwelcome.enabled", false);
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.sessionstore.resume_from_crash", false);

// blank new-tab page (address bar is hidden, so no navigation from it)
user_pref("browser.newtabpage.enabled", false);

// Alt must not reveal the menu bar
user_pref("ui.key.menuAccessKeyFocuses", false);

// the nav bar is squashed to 1px (not hidden) so save-password popups keep
// their anchor; make sure keyboard focus can never wander into it
user_pref("browser.toolbars.keyboard_navigation", false);

// kiosk sites served over plain http (a LAN ERP, say) must behave like any
// other kiosk site: no "connection is not secure" warning dropdown on the
// login fields, and saved passwords DO autofill (Firefox refuses to autofill
// on http pages by default -- pointless for a fixed site on a trusted LAN)
user_pref("security.insecure_field_warning.contextual.enabled", false);
user_pref("signon.autofillForms.http", true);

// quiet: no update prompts or telemetry
user_pref("app.update.auto", false);
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("datareporting.healthreport.uploadEnabled", false);
