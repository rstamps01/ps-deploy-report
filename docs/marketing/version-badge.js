/* Shared version badge for the marketing site.
 *
 * Rewrites every element carrying a `data-app-version` attribute with the tag
 * of the latest published GitHub Release, so the pages never drift from what is
 * actually shipping. The markup keeps a hardcoded version as its text, which
 * stays visible when the API is unreachable (offline, rate-limited, or blocked
 * by a corporate proxy) — a slightly stale badge beats an empty one.
 *
 * Results are cached in sessionStorage because a reader moving between the
 * three pages would otherwise spend three of the 60 unauthenticated requests
 * per hour that GitHub allows per IP.
 */
(function () {
    var API = 'https://api.github.com/repos/rstamps01/ps-deploy-report/releases/latest';
    var CACHE_KEY = 'psdr-latest-version';

    function apply(version) {
        if (!version) return;
        var els = document.querySelectorAll('[data-app-version]');
        for (var i = 0; i < els.length; i++) {
            els[i].textContent = version;
        }
    }

    function normalize(tag) {
        if (!tag) return null;
        return tag.charAt(0) === 'v' ? tag : 'v' + tag;
    }

    function cached() {
        try {
            return window.sessionStorage.getItem(CACHE_KEY);
        } catch (e) {
            return null; // private mode / storage disabled
        }
    }

    function remember(version) {
        try {
            window.sessionStorage.setItem(CACHE_KEY, version);
        } catch (e) {
            /* non-fatal */
        }
    }

    var hit = cached();
    if (hit) {
        apply(hit);
        return;
    }

    fetch(API)
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) {
            var version = d && normalize(d.tag_name);
            if (!version) return;
            remember(version);
            apply(version);
        })
        .catch(function () { /* keep the hardcoded fallback */ });
})();
