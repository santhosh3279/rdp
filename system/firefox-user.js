// kiosk profile prefs, copied into each user's profile on every browser start.
// Managed by kiosk-admin: edit /etc/kiosk/firefox-user.js, not the profile copy.

// required for userChrome.css (the tab-strip-only skin) to load
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);

// tabs merge into the titlebar = tab strip sits at the very top of the screen
user_pref("browser.tabs.inTitlebar", 1);

// Ctrl+W on the last tab must not kill the window
user_pref("browser.tabs.closeWindowWithLastTab", false);

// no first-run tour, default-browser nag, or crash-restore prompts
user_pref("browser.aboutwelcome.enabled", false);
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.sessionstore.resume_from_crash", false);

// blank new-tab page (address bar is hidden, so no navigation from it)
user_pref("browser.newtabpage.enabled", false);

// Alt must not reveal the menu bar
user_pref("ui.key.menuAccessKeyFocuses", false);

// quiet: no update prompts or telemetry
user_pref("app.update.auto", false);
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("datareporting.healthreport.uploadEnabled", false);
