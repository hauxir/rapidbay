(function () {
    var keylistener = function (e) {
        var keycode = e.keyCode ? e.keyCode : e.which;
        var name = e.key;
        var lowername = name.toLowerCase();
        if (lowername === "enter") {
            e.preventDefault();
            document.activeElement.click();
        }
        if (lowername === "arrowdown" || lowername === "arrowright") {
            document.body.onmouseover = null;
            e.preventDefault();
            focusNextElement();
        }
        if (lowername === "arrowup" || lowername === "arrowleft") {
            document.body.onmouseover = null;
            e.preventDefault();
            focusPrevElement();
        }
        if (lowername === "backspace") {
            e.preventDefault();
            e.stopPropagation();
            window.history.back();
        }
    };

    function focusNextElement() {
        var selectables = $(':focusable:not([tabindex="-1"])');
        var currentIndex = selectables.index($(":focus"));
        document.activeElement.blur();
        selectables.eq(currentIndex + 1).focus();
    }

    function focusPrevElement() {
        var selectables = $(':focusable:not([tabindex="-1"])');
        var currentIndex = selectables.index($(":focus"));
        document.activeElement.blur();
        selectables.eq(currentIndex - 1).focus();
    }

    document.addEventListener("mousemove", function () {
        if (document.activeElement && document.activeElement.tagName !== "INPUT") {
            document.activeElement.blur();
        }
    });

    window.isSafari =
        navigator.vendor && navigator.vendor.indexOf("Apple") > -1;

    window.isChrome = /Chrome/i.test(navigator.userAgent);
    if (navigator.serviceWorker) {
        navigator.serviceWorker.register("/sw.js");
    }

    if (!window.location.origin) {
        window.location.origin =
            window.location.protocol +
            "//" +
            window.location.hostname +
            (window.location.port ? ":" + window.location.port : "");
    }

    if (!String.prototype.startsWith) {
        String.prototype.startsWith = function (search, pos) {
            return this.slice(pos || 0, search.length) === search;
        };
    }

    var pending_callbacks = [];
    var pending_requests = [];

    function rbsetTimeout(f, s) {
        clear_pending_callbacks();
        pending_callbacks.push(setTimeout(f, s));
    }

    function clear_pending_callbacks() {
        while (pending_callbacks.length) {
            var f = pending_callbacks.pop();
            clearTimeout(f);
        }
    }

    function clear_pending_requests() {
        while (pending_requests.length) {
            var r = pending_requests.pop();
            r.abort();
        }
    }

    function get(url, callback) {
        var request;
        if (!document.cookie) {
            document.cookie = localStorage.getItem("cookie");
        }
        function _callback(data) {
            pending_requests = pending_requests.filter(function (req) {
                req !== request;
            });
            callback(data);
        }
        request = $.get(url, _callback);
        pending_requests.push(request);
        return request;
    }

    function post(url, data, callback) {
        if (!document.cookie) {
            document.cookie = localStorage.getItem("cookie");
        }
        $.post(url, data, callback);
    }

    // Subscribe to a server-sent-events endpoint. Calls callback per event,
    // closes on {done: true}, and invokes fallback (e.g. to start polling)
    // if SSE is unavailable or the stream errors.
    function subscribe(url, callback, fallback) {
        if (!window.EventSource) {
            fallback();
            return null;
        }
        if (!document.cookie) {
            document.cookie = localStorage.getItem("cookie");
        }
        var es = new EventSource(url);
        es.onmessage = function (e) {
            var data = JSON.parse(e.data);
            if (data.done) {
                es.close();
            }
            callback(data);
        };
        es.onerror = function () {
            es.close();
            fallback();
        };
        return es;
    }

    function reportLibraryEvents(events) {
        if (!events || !events.length) {
            return;
        }
        if (!document.cookie) {
            document.cookie = localStorage.getItem("cookie");
        }
        $.ajax({
            url: "/api/library/observe/",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({ events: events }),
        });
    }

    function syncLibraryFromLocalHistory() {
        if (window.sessionStorage.getItem("rapidbayLibrarySync")) {
            return;
        }
        window.sessionStorage.setItem("rapidbayLibrarySync", "1");
        var events = [];
        var magnetsByHash = {};
        getHistory().forEach(function (entry) {
            if (!entry || !entry.magnet) {
                return;
            }
            magnetsByHash[get_hash(entry.magnet)] = entry.magnet;
            events.push({
                event: "download",
                magnet: entry.magnet,
                title: entry.title || "",
                filename: "",
                ts: entry.ts || 0,
            });
        });
        getFavorites().forEach(function (entry) {
            if (!entry || !entry.magnet) {
                return;
            }
            magnetsByHash[get_hash(entry.magnet)] = entry.magnet;
            events.push({
                event: "download",
                magnet: entry.magnet,
                title: entry.title || "",
                filename: entry.filename || "",
                ts: entry.ts || 0,
            });
        });
        var completed = JSON.parse(localStorage.getItem("completedFiles") || "{}");
        Object.keys(completed).forEach(function (hash) {
            var magnet = magnetsByHash[hash] || ("magnet:?xt=urn:btih:" + hash);
            (completed[hash] || []).forEach(function (filename) {
                events.push({
                    event: "watched",
                    magnet: magnet,
                    title: filename,
                    filename: filename,
                    ts: 0,
                });
            });
        });
        reportLibraryEvents(events);
    }

    function saveToHistory(magnet) {
        var history = JSON.parse(localStorage.getItem("downloadHistory") || "[]");
        history = history.filter(function (h) {
            return h.magnet !== magnet;
        });
        var title = get_magnet_name(magnet);
        history.unshift({ magnet: magnet, title: title, ts: Date.now() });
        if (history.length > 50) {
            history = history.slice(0, 50);
        }
        localStorage.setItem("downloadHistory", JSON.stringify(history));
    }

    function getHistory() {
        return JSON.parse(localStorage.getItem("downloadHistory") || "[]");
    }

    function clearHistory() {
        localStorage.removeItem("downloadHistory");
        localStorage.removeItem("completedFiles");
        localStorage.removeItem("searchHistory");
    }

    function saveSearchTerm(term) {
        if (!term || term.trim() === "") return;
        var history = JSON.parse(localStorage.getItem("searchHistory") || "[]");
        history = history.filter(function (t) {
            return t.toLowerCase() !== term.toLowerCase();
        });
        history.unshift(term);
        if (history.length > 8) {
            history = history.slice(0, 8);
        }
        localStorage.setItem("searchHistory", JSON.stringify(history));
        reportLibraryEvents([{
            event: "search",
            title: term.trim(),
            filename: "",
            ts: Date.now(),
        }]);
    }

    function getSearchHistory() {
        return JSON.parse(localStorage.getItem("searchHistory") || "[]").slice(0, 8);
    }

    function clearSearchHistory() {
        localStorage.removeItem("searchHistory");
    }

    function markFileCompleted(magnet, filename) {
        var hash = get_hash(magnet);
        var completed = JSON.parse(localStorage.getItem("completedFiles") || "{}");
        if (!completed[hash]) completed[hash] = [];
        if (completed[hash].indexOf(filename) === -1) {
            completed[hash].push(filename);
        }
        localStorage.setItem("completedFiles", JSON.stringify(completed));
        var completedAt = JSON.parse(localStorage.getItem("completedAt") || "{}");
        completedAt[hash + "\n" + filename] = Date.now();
        localStorage.setItem("completedAt", JSON.stringify(completedAt));
        reportLibraryEvents([{
            event: "watched",
            magnet: magnet,
            title: filename,
            filename: filename,
            ts: Date.now(),
        }]);
    }

    function getCompletedFiles(magnet) {
        var hash = get_hash(magnet);
        var completed = JSON.parse(localStorage.getItem("completedFiles") || "{}");
        return completed[hash] || [];
    }

    function getFavorites() {
        var favorites = JSON.parse(localStorage.getItem("favorites") || "[]");
        return favorites.sort(function (a, b) {
            return (a.title || "").localeCompare(b.title || "");
        });
    }

    function saveFavorite(magnet, filename) {
        var magnetHash = get_hash(magnet);
        var favorites = JSON.parse(localStorage.getItem("favorites") || "[]");
        favorites = favorites.filter(function (f) {
            return get_hash(f.magnet) !== magnetHash || f.filename !== filename;
        });
        var title = filename || get_magnet_name(magnet);
        favorites.unshift({ magnet: magnet, filename: filename, title: title, ts: Date.now() });
        if (favorites.length > 100) {
            favorites = favorites.slice(0, 100);
        }
        localStorage.setItem("favorites", JSON.stringify(favorites));
    }

    function removeFavorite(magnet, filename) {
        var magnetHash = get_hash(magnet);
        var favorites = JSON.parse(localStorage.getItem("favorites") || "[]");
        favorites = favorites.filter(function (f) {
            return get_hash(f.magnet) !== magnetHash || f.filename !== filename;
        });
        localStorage.setItem("favorites", JSON.stringify(favorites));
    }

    function getVideoPositionKey(magnet, filename) {
        return "videoPosition_" + get_hash(magnet) + "_" + filename;
    }

    function readStoredProgress(key) {
        var raw = localStorage.getItem(key);
        if (!raw) {
            return { position: 0, duration: 0, ts: 0 };
        }
        if (raw.charAt(0) === "{") {
            try {
                var data = JSON.parse(raw);
                return {
                    position: parseFloat(data.position) || 0,
                    duration: parseFloat(data.duration) || 0,
                    ts: parseInt(data.ts, 10) || 0,
                };
            } catch (error) {
                return { position: 0, duration: 0, ts: 0 };
            }
        }
        return { position: parseFloat(raw) || 0, duration: 0, ts: 0 };
    }

    function saveVideoPosition(magnet, filename, position, duration) {
        var previous = readStoredProgress(getVideoPositionKey(magnet, filename));
        localStorage.setItem(getVideoPositionKey(magnet, filename), JSON.stringify({
            position: position,
            duration: duration || previous.duration || 0,
            ts: Date.now(),
        }));
    }

    function getVideoPosition(magnet, filename) {
        return readStoredProgress(getVideoPositionKey(magnet, filename)).position;
    }

    function progressCountsAsWatched(position, duration) {
        if (!isFinite(duration) || duration <= 0 || !(position > 0)) {
            return false;
        }
        if (position / duration >= 0.98) {
            return true;
        }
        return duration >= 120 && duration - position < 120;
    }

    var progressReportAt = {};

    function reportPlaybackProgress(magnet, filename, position, duration, force) {
        if (!magnet || !filename || !(position > 120) || progressCountsAsWatched(position, duration)) {
            return;
        }
        var key = get_hash(magnet) + ":" + filename;
        var now = Date.now();
        if (!force && progressReportAt[key] && now - progressReportAt[key] < 30000) {
            return;
        }
        progressReportAt[key] = now;
        reportLibraryEvents([{
            event: "progress",
            magnet: magnet,
            title: filename,
            filename: filename,
            ts: now,
            position: Math.round(position),
            duration: Math.round(duration || 0),
        }]);
    }

    function magnetForHash(hash) {
        var lists = getHistory().concat(getFavorites());
        for (var i = 0; i < lists.length; i++) {
            if (lists[i] && lists[i].magnet && get_hash(lists[i].magnet) === hash) {
                return lists[i].magnet;
            }
        }
        return "magnet:?xt=urn:btih:" + hash;
    }

    function collectInProgressEvents() {
        var events = [];
        var cutoff = Date.now() - 14 * 24 * 60 * 60 * 1000;
        for (var i = localStorage.length - 1; i >= 0; i--) {
            var key = localStorage.key(i);
            if (!key || key.indexOf("videoPosition_") !== 0) {
                continue;
            }
            var rest = key.slice("videoPosition_".length);
            var splitAt = rest.indexOf("_");
            if (splitAt < 1) {
                continue;
            }
            var hash = rest.slice(0, splitAt);
            var filename = rest.slice(splitAt + 1);
            var stored = readStoredProgress(key);
            if (!(stored.position > 120) || progressCountsAsWatched(stored.position, stored.duration)) {
                continue;
            }
            var completed = JSON.parse(localStorage.getItem("completedFiles") || "{}");
            var finishedNames = completed[hash] || [];
            if (finishedNames.indexOf(filename) !== -1) {
                var completedAt = JSON.parse(localStorage.getItem("completedAt") || "{}");
                var finishedAt = parseInt(completedAt[hash + "\n" + filename], 10) || 0;
                var leftover = !stored.duration || (finishedAt && stored.ts && stored.ts <= finishedAt);
                if (leftover) {
                    localStorage.removeItem(key);
                    continue;
                }
            }
            if (!stored.ts) {
                stored.ts = Date.now();
                localStorage.setItem(key, JSON.stringify({
                    position: stored.position,
                    duration: stored.duration,
                    ts: stored.ts,
                }));
            }
            if (stored.ts < cutoff) {
                continue;
            }
            events.push({
                event: "progress",
                magnet: magnetForHash(hash),
                title: filename,
                filename: filename,
                ts: stored.ts || Date.now(),
                position: Math.round(stored.position),
                duration: Math.round(stored.duration || 0),
            });
        }
        return events;
    }

    function clearVideoPosition(magnet, filename) {
        localStorage.removeItem(getVideoPositionKey(magnet, filename));
    }

    function get_hash(magnet_link) {
        var hash_start = magnet_link.indexOf("btih:") + 5;
        var hash_end = magnet_link.indexOf("&");
        if (hash_end == -1) return magnet_link.substr(hash_start).toLowerCase();
        return magnet_link
            .substr(hash_start, hash_end - hash_start)
            .toLowerCase();
    }

    function get_magnet_name(magnet_link) {
        var match = magnet_link.match(/dn=([^&]+)/);
        if (match) {
            return decodeURIComponent(match[1].replace(/\+/g, " "));
        }
        return get_hash(magnet_link);
    }

    var EXECUTABLE_EXTENSIONS = {
        exe: 1, bat: 1, cmd: 1, com: 1, msi: 1, msp: 1, scr: 1, pif: 1, cpl: 1,
        ps1: 1, vbs: 1, vbe: 1, js: 1, jse: 1, wsf: 1, wsh: 1, hta: 1,
        sh: 1, bash: 1, command: 1, bin: 1, run: 1, apk: 1, jar: 1,
        dll: 1, sys: 1, msc: 1, reg: 1, lnk: 1, gadget: 1
    };

    function isExecutableFilename(filename) {
        var base = String(filename || "").split(/[/\\]/).pop();
        var dot = base.lastIndexOf(".");
        if (dot < 0) {
            return false;
        }
        return !!EXECUTABLE_EXTENSIONS[base.slice(dot + 1).toLowerCase()];
    }

    var VIDEO_EXTENSIONS = {
        mkv: 1, mp4: 1, avi: 1, m4v: 1, webm: 1, mov: 1, wmv: 1, mpg: 1, mpeg: 1, ts: 1, m2ts: 1
    };

    function isVideoFilename(filename) {
        var base = String(filename || "").split(/[/\\]/).pop();
        var dot = base.lastIndexOf(".");
        if (dot < 0) {
            return false;
        }
        return !!VIDEO_EXTENSIONS[base.slice(dot + 1).toLowerCase()];
    }

    function rememberEpisodeTarget(season, episode) {
        var seasonNumber = parseInt(season, 10);
        var episodeNumber = parseInt(episode, 10);
        if (isNaN(seasonNumber) || isNaN(episodeNumber)) {
            sessionStorage.removeItem("rapidbayEpisodeTarget");
            return;
        }
        sessionStorage.setItem("rapidbayEpisodeTarget", JSON.stringify({
            season: seasonNumber,
            episode: episodeNumber,
        }));
    }

    function readEpisodeTarget() {
        try {
            var parsed = JSON.parse(sessionStorage.getItem("rapidbayEpisodeTarget") || "null");
            if (!parsed) {
                return null;
            }
            var seasonNumber = parseInt(parsed.season, 10);
            var episodeNumber = parseInt(parsed.episode, 10);
            if (isNaN(seasonNumber) || isNaN(episodeNumber)) {
                return null;
            }
            return { season: seasonNumber, episode: episodeNumber };
        } catch (error) {
            return null;
        }
    }

    function fileMatchesEpisode(filename, season, episode) {
        var name = String(filename || "");
        var code = new RegExp("(?:^|[^A-Za-z0-9])S0*" + season + "(?!\\d)[\\s._-]*E0*" + episode + "(?!\\d)", "i");
        var cross = new RegExp("(?:^|[^0-9])0*" + season + "[xX]0*" + episode + "(?!\\d)");
        var words = new RegExp("\\bseason[\\s._-]*0*" + season + "\\b[\\s\\S]{0,40}?\\bepisode[\\s._-]*0*" + episode + "\\b", "i");
        return code.test(name) || cross.test(name) || words.test(name);
    }

    function pickEpisodeFile(files, season, episode) {
        var matches = (files || []).filter(function (name) {
            return fileMatchesEpisode(name, season, episode) && !isExecutableFilename(name);
        });
        var fresh = matches.filter(function (name) {
            return !/\bsample\b/i.test(name);
        });
        if (fresh.length) {
            matches = fresh;
        }
        var videos = matches.filter(isVideoFilename);
        if (videos.length === 1) {
            return videos[0];
        }
        if (videos.length > 1) {
            return null;
        }
        return matches.length === 1 ? matches[0] : null;
    }

    function pinnedTitleFromLocation() {
        var params = new URLSearchParams(window.location.search);
        var media = params.get("media");
        var tmdb = params.get("tmdb");
        if ((media === "tv" || media === "movie") && /^\d+$/.test(tmdb || "")) {
            return { media: media, tmdb: tmdb };
        }
        return null;
    }

    function navigate(path, replaceState) {
        if (replaceState) {
            router.historyAPIUpdateMethod("replaceState");
        } else {
            router.historyAPIUpdateMethod("pushState");
        }
        router.navigate(path);
    }

    var rbmixin = {
        props: ["params"],
        methods: {
            navigate: navigate,
        },
    };

    Vue.component("loading-spinner", {
        props: ["heading", "subheading", "progress"],
        template: "#loading-spinner-template",
        updated: function () {
            var progress_el = this.$refs.progress;
            progress_el &&
                (progress_el.style.width = this.progress * 100 + "%");
        },
    });

    var LANGUAGE_ALIASES = {
        pb: "pt",
        jp: "ja",
        gr: "el",
        cz: "cs",
        dk: "da",
        se: "sv",
        kr: "ko",
        cn: "zh",
    };

    function languageName(code) {
        var raw = String(code || "").trim();
        if (!raw) {
            return raw;
        }
        var normalized = raw.replace(/_/g, "-");
        if (!/^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$/.test(normalized)) {
            return raw;
        }
        var alias = LANGUAGE_ALIASES[normalized.toLowerCase()];
        if (alias) {
            normalized = alias;
        }
        try {
            var name = new Intl.DisplayNames(["en"], { type: "language" }).of(normalized);
            if (name && name.toLowerCase() !== normalized.toLowerCase() && name.toLowerCase() !== "root") {
                return name;
            }
        } catch (error) {}
        if (/^[A-Za-z]{2}$/.test(normalized)) {
            try {
                var region = new Intl.DisplayNames(["en"], { type: "region" }).of(normalized.toUpperCase());
                if (region && region.toLowerCase() !== normalized.toLowerCase()) {
                    return region;
                }
            } catch (error) {}
        }
        return raw;
    }

    function cleanMediaTitle(name) {
        var text = String(name || "");
        try {
            text = decodeURIComponent(text);
        } catch (error) {
            text = String(name || "");
        }
        return text
            .split(/[/\\]/).pop()
            .replace(/\.[a-z0-9]{2,4}$/i, "")
            .replace(/\[[^\]]*\]/g, "")
            .replace(/[._]+/g, " ")
            .replace(/\s+/g, " ")
            .trim();
    }

    function episodeCode(text) {
        var source = String(text || "");
        var match = source.match(/S0*(\d{1,2})[\s._-]*E0*(\d{1,3})(?!\d)/i);
        if (match) {
            return { season: parseInt(match[1], 10), episode: parseInt(match[2], 10) };
        }
        match = source.match(/(?:^|[^0-9])0*(\d{1,2})x0*(\d{1,3})(?!\d)/i);
        if (match) {
            return { season: parseInt(match[1], 10), episode: parseInt(match[2], 10) };
        }
        return null;
    }

    function releaseSignature(display) {
        var text = String(display || "");
        var quality = text.match(/\b\d{3,4}p\b[\s\S]*$/i);
        if (quality) {
            return quality[0].replace(/\s+/g, " ").trim().toLowerCase();
        }
        return text
            .replace(/S0*\d{1,2}[\s._-]*E0*\d{1,3}/ig, " ")
            .replace(/\bS0*\d{1,2}\b/ig, " ")
            .replace(/\s+/g, " ")
            .trim()
            .toLowerCase();
    }

    function releaseGroup(display) {
        var signature = releaseSignature(display);
        var token = signature.split(/\s+/).pop() || "";
        var piece = token.split("-").pop();
        if (/^[a-z0-9]{3,}$/i.test(piece) && !/^(x|h)26[45]$/i.test(piece) && !/^\d{3,4}p$/i.test(piece)) {
            return piece;
        }
        return token;
    }

    function showNameFromDisplay(display) {
        var show = String(display || "").split(/S0*\d{1,2}[\s._-]*E0*\d{1,3}/i)[0];
        return show.replace(/\bS0*\d{1,2}\b/i, "").replace(/\s+/g, " ").trim();
    }

    function releaseSearchTerm(display) {
        var show = String(display || "").split(/S0*\d{1,2}[\s._-]*E0*\d{1,3}/i)[0];
        show = show.replace(/\bS0*\d{1,2}\b/i, "").replace(/\s+/g, " ").trim();
        return [show, releaseGroup(display)].filter(Boolean).join(" ");
    }

    function addReleaseEpisode(list, episode) {
        for (var i = 0; i < list.length; i++) {
            if (list[i].season === episode.season && list[i].episode === episode.episode) {
                if (episode.current) {
                    list[i] = episode;
                }
                return;
            }
        }
        list.push(episode);
    }

    function episodesFromNames(names, signature, magnet, currentFile) {
        var currentBase = String(currentFile || "").split(/[/\\]/).pop().toLowerCase();
        var list = [];
        (names || []).forEach(function (name) {
            if (!isVideoFilename(name)) {
                return;
            }
            var display = cleanMediaTitle(name);
            if (!signature || releaseSignature(display) !== signature) {
                return;
            }
            var code = episodeCode(name) || episodeCode(display);
            if (!code) {
                return;
            }
            var base = String(name).split(/[/\\]/).pop().toLowerCase();
            list.push({
                label: display,
                name: "",
                overview: "",
                stillUrl: "",
                season: code.season,
                episode: code.episode,
                magnet: magnet,
                filename: name,
                torrentLink: "",
                current: base === currentBase,
            });
        });
        return list;
    }

    Vue.component("player", {
        props: ["supported", "url", "subtitles", "back", "magnet", "filename", "downloadProgress", "downloadStatus", "onStreamError"],
        data: function () {
            return {
                isDesktop:
                    !/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini|Mobile|mobile|CriOS/i.test(
                        navigator.userAgent
                    ),
                isChrome: window.isChrome,
                hovering: false,
                openMenu: "",
                paused: false,
                currentTime: 0,
                duration: 0,
                volume: 1,
                muted: false,
                captionChoices: [],
                activeCaption: null,
                audioChoices: [],
                activeAudio: null,
                nextFilename: "",
                nextMagnet: null,
                episodeChoices: [],
                episodesLoading: false,
                episodesLoaded: false,
                episodeShowTitle: "",
                focusedEpisodeKey: "",
            };
        },
        computed: {
            downloadStatusLabel: function () {
                if (!this.downloadStatus) return "";
                var text = this.downloadStatus.replace(/_/g, " ");
                return text.charAt(0).toUpperCase() + text.slice(1);
            },
            controlsOn: function () {
                return this.hovering || !!this.openMenu;
            },
            displayTitle: function () {
                var name = this.filename || "";
                try {
                    name = decodeURIComponent(name);
                } catch (error) {
                    name = this.filename || "";
                }
                return name
                    .replace(/\.[a-z0-9]{2,4}$/i, "")
                    .replace(/\[[^\]]*\]/g, "")
                    .replace(/[._]+/g, " ")
                    .replace(/\s+/g, " ")
                    .trim();
            },
            remainingLabel: function () {
                if (!this.duration) {
                    return "0:00";
                }
                return this.formatClock(Math.max(0, this.duration - this.currentTime));
            },
            episodeGroups: function () {
                var groups = [];
                var index = {};
                this.episodeChoices.forEach(function (episode) {
                    var key = String(episode.season);
                    if (!index[key]) {
                        index[key] = { season: episode.season, episodes: [] };
                        groups.push(index[key]);
                    }
                    index[key].episodes.push(episode);
                });
                return groups;
            },
            scrubValue: function () {
                if (!this.duration) {
                    return 0;
                }
                return Math.round((this.currentTime / this.duration) * 1000);
            },
            progressPercent: function () {
                return (this.scrubValue / 10) + "%";
            },
        },
        watch: {
            controlsOn: function (shown) {
                this.placeCues(shown);
            },
            // url changes within the same playback session when subs become
            // available (cache-buster increments). Reload hls.js's source in
            // place — the parent's :key strips the query string so we don't
            // remount the <video> here. Playback time and play/pause state
            // are preserved across the reload.
            url: function (newUrl, oldUrl) {
                if (!newUrl || newUrl === oldUrl) return;
                if (newUrl.split("?")[0] !== oldUrl.split("?")[0]) return;
                var video = document.getElementsByTagName("video")[0];
                if (!video) return;
                var fullUrl = window.location.origin + newUrl;
                var resumeAt = video.currentTime;
                var wasPlaying = !video.paused && !video.ended;
                if (this.hls) {
                    var hls = this.hls;
                    var seeked = false;
                    var resume = function () {
                        if (seeked) return;
                        seeked = true;
                        hls.off(Hls.Events.MANIFEST_PARSED, resume);
                        if (resumeAt > 0) {
                            video.currentTime = resumeAt;
                        }
                        if (wasPlaying) {
                            video.play().catch(function () {});
                        }
                    };
                    hls.once(Hls.Events.MANIFEST_PARSED, resume);
                    hls.loadSource(fullUrl);
                } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
                    var onLoaded = function () {
                        video.removeEventListener("loadedmetadata", onLoaded);
                        if (resumeAt > 0) {
                            video.currentTime = resumeAt;
                        }
                        if (wasPlaying) {
                            video.play().catch(function () {});
                        }
                    };
                    video.addEventListener("loadedmetadata", onLoaded);
                    video.src = fullUrl;
                }
            },
        },
        methods: {
            languageName: languageName,
            formatClock: function (seconds) {
                seconds = Math.max(0, Math.floor(seconds || 0));
                var hours = Math.floor(seconds / 3600);
                var minutes = Math.floor((seconds % 3600) / 60);
                var secs = seconds % 60;
                function pad(value) {
                    return (value < 10 ? "0" : "") + value;
                }
                if (hours > 0) {
                    return hours + ":" + pad(minutes) + ":" + pad(secs);
                }
                return minutes + ":" + pad(secs);
            },
            videoEl: function () {
                return this.$el ? this.$el.querySelector("video") : null;
            },
            syncPlayback: function () {
                var video = this.videoEl();
                if (!video) {
                    return;
                }
                this.paused = video.paused;
                this.currentTime = video.currentTime || 0;
                this.duration = isFinite(video.duration) ? video.duration : 0;
                this.volume = video.volume;
                this.muted = video.muted || video.volume === 0;
            },
            togglePlay: function () {
                this.openMenu = "";
                var video = this.videoEl();
                if (!video) {
                    return;
                }
                if (video.paused) {
                    video.play();
                } else {
                    video.pause();
                }
            },
            seekBy: function (seconds) {
                var video = this.videoEl();
                if (!video) {
                    return;
                }
                var next = video.currentTime + seconds;
                if (isFinite(video.duration)) {
                    next = Math.min(video.duration, next);
                }
                video.currentTime = Math.max(0, next);
                this.syncPlayback();
            },
            onScrub: function (event) {
                var video = this.videoEl();
                if (!video || !isFinite(video.duration) || video.duration <= 0) {
                    return;
                }
                video.currentTime = (Number(event.target.value) / 1000) * video.duration;
                this.syncPlayback();
            },
            toggleMute: function () {
                var video = this.videoEl();
                if (!video) {
                    return;
                }
                video.muted = !video.muted;
                if (!video.muted && video.volume === 0) {
                    video.volume = 1;
                }
                this.syncPlayback();
            },
            setVolume: function (event) {
                var video = this.videoEl();
                if (!video) {
                    return;
                }
                video.volume = Number(event.target.value);
                video.muted = video.volume === 0;
                this.syncPlayback();
            },
            toggleMenu: function (name) {
                this.hovering = true;
                this.openMenu = this.openMenu === name ? "" : name;
                if (this.openMenu === "episodes") {
                    this.loadEpisodes();
                    this.focusPlayingEpisode();
                }
            },
            focusPlayingEpisode: function () {
                var self = this;
                this.$nextTick(function () {
                    if (self.openMenu !== "episodes") {
                        return;
                    }
                    var button = self.$el.querySelector(".player-episode.current") || self.$el.querySelector(".player-episode");
                    if (!button) {
                        return;
                    }
                    if (button.focus) {
                        button.focus({ preventScroll: true });
                    }
                    self.revealEpisodeButton(button);
                });
            },
            revealEpisodeButton: function (button) {
                var self = this;
                this.$nextTick(function () {
                    var scroller = self.$el.querySelector(".player-episode-scroll");
                    if (!scroller || !button) {
                        return;
                    }
                    var scrollerRect = scroller.getBoundingClientRect();
                    var buttonRect = button.getBoundingClientRect();
                    if (buttonRect.height >= scroller.clientHeight) {
                        scroller.scrollTop += buttonRect.top - scrollerRect.top;
                        return;
                    }
                    if (buttonRect.top < scrollerRect.top) {
                        scroller.scrollTop -= scrollerRect.top - buttonRect.top;
                    } else if (buttonRect.bottom > scrollerRect.bottom) {
                        scroller.scrollTop += buttonRect.bottom - scrollerRect.bottom;
                    }
                });
            },
            onEpisodeKeydown: function (event) {
                var key = event.key.toLowerCase();
                if (key !== "arrowdown" && key !== "arrowup") {
                    return;
                }
                var buttons = this.$el.querySelectorAll(".player-episode");
                if (!buttons.length) {
                    return;
                }
                event.preventDefault();
                event.stopPropagation();
                var index = 0;
                for (var i = 0; i < buttons.length; i++) {
                    if (buttons[i] === document.activeElement) {
                        index = i;
                    }
                }
                var next = key === "arrowdown" ? Math.min(buttons.length - 1, index + 1) : Math.max(0, index - 1);
                var button = buttons[next];
                var season = Number(button.getAttribute("data-season"));
                var episodeNumber = Number(button.getAttribute("data-episode"));
                var episode = null;
                this.episodeChoices.forEach(function (item) {
                    if (item.season === season && item.episode === episodeNumber) {
                        episode = item;
                    }
                });
                if (episode) {
                    this.focusEpisode(episode);
                }
                if (button.focus) {
                    button.focus({ preventScroll: true });
                }
                this.revealEpisodeButton(button);
            },
            focusEpisode: function (episode, event) {
                this.focusedEpisodeKey = episode.season + "-" + episode.episode;
                var button = event && event.currentTarget;
                if (button && button.focus && document.activeElement !== button) {
                    button.focus({ preventScroll: true });
                }
                this.revealEpisodeButton(button || document.activeElement);
            },
            isEpisodeFocused: function (episode) {
                return this.focusedEpisodeKey === episode.season + "-" + episode.episode;
            },
            loadEpisodeDetails: function (list, showName) {
                var self = this;
                function apply(tmdbId, showTitle) {
                    self.episodeShowTitle = showTitle || showName;
                    var seasons = [];
                    list.forEach(function (episode) {
                        if (seasons.indexOf(episode.season) === -1) {
                            seasons.push(episode.season);
                        }
                    });
                    var left = seasons.length;
                    if (!left) {
                        return;
                    }
                    seasons.forEach(function (season) {
                        get("/api/tv/" + tmdbId + "/season/" + season + "/", function (payload) {
                            var episodes = (payload && payload.episodes) || [];
                            episodes.forEach(function (details) {
                                list.forEach(function (item) {
                                    if (item.season === season && item.episode === details.episode_number) {
                                        item.name = details.name || item.name;
                                        item.overview = details.overview || "";
                                        item.stillUrl = details.still_url || "";
                                    }
                                });
                            });
                            left -= 1;
                            if (left === 0) {
                                self.episodeChoices = list.slice();
                            }
                        });
                    });
                }
                get("/api/library/", function (data) {
                    var titles = (data && data.titles) || [];
                    var folded = String(showName || "").toLowerCase();
                    var match = null;
                    for (var i = 0; i < titles.length; i++) {
                        if (titles[i].media_type === "tv" && String(titles[i].title || "").toLowerCase() === folded) {
                            match = titles[i];
                            break;
                        }
                    }
                    if (match) {
                        apply(match.tmdb_id, match.title);
                        return;
                    }
                    get("/api/tv/lookup/?q=" + encodeURIComponent(showName), function (found) {
                        if (found && found.tmdb_id) {
                            apply(found.tmdb_id, found.title);
                        }
                    });
                });
            },
            loadEpisodes: function () {
                if (this.episodesLoading || this.episodesLoaded) {
                    return;
                }
                var self = this;
                var currentFile = this.filename || "";
                try {
                    currentFile = decodeURIComponent(currentFile);
                } catch (error) {
                    currentFile = this.filename || "";
                }
                var currentDisplay = cleanMediaTitle(currentFile);
                var signature = releaseSignature(currentDisplay);
                var currentCode = episodeCode(currentFile) || episodeCode(currentDisplay);
                var magnet = this.magnet || "";
                this.episodesLoading = true;
                function finish(list) {
                    if (currentCode && !list.some(function (episode) { return episode.current; })) {
                        addReleaseEpisode(list, {
                            label: currentDisplay,
                            name: "",
                            overview: "",
                            stillUrl: "",
                            season: currentCode.season,
                            episode: currentCode.episode,
                            magnet: magnet,
                            filename: currentFile,
                            torrentLink: "",
                            current: true,
                        });
                    }
                    list.sort(function (a, b) {
                        if (a.season !== b.season) {
                            return a.season - b.season;
                        }
                        return a.episode - b.episode;
                    });
                    self.episodeChoices = list;
                    self.episodesLoading = false;
                    self.episodesLoaded = true;
                    var focused = null;
                    for (var i = 0; i < list.length; i++) {
                        if (list[i].current) {
                            focused = list[i];
                        }
                    }
                    if (!focused && list.length) {
                        focused = list[0];
                    }
                    self.focusedEpisodeKey = focused ? focused.season + "-" + focused.episode : "";
                    self.loadEpisodeDetails(list, showNameFromDisplay(currentDisplay));
                    self.focusPlayingEpisode();
                }
                var hash = (this.url || "").split("/")[2];
                get("/api/magnet/" + hash + "/", function (data) {
                    var found = episodesFromNames(data && data.files, signature, magnet, currentFile);
                    if (!currentCode || found.length > 1) {
                        finish(found);
                        return;
                    }
                    var term = releaseSearchTerm(currentDisplay);
                    get("/api/search/" + encodeURIComponent(term), function (payload) {
                        var results = (payload && payload.results) || [];
                        var packs = [];
                        results.forEach(function (result) {
                            var title = result.title || "";
                            var display = cleanMediaTitle(title);
                            if (releaseSignature(display) !== signature) {
                                return;
                            }
                            var code = episodeCode(title) || episodeCode(display);
                            if (code) {
                                addReleaseEpisode(found, {
                                    label: display,
                                    name: "",
                                    overview: "",
                                    stillUrl: "",
                                    season: code.season,
                                    episode: code.episode,
                                    magnet: result.magnet || "",
                                    filename: "",
                                    torrentLink: result.magnet ? "" : (result.torrent_link || ""),
                                    current: false,
                                });
                                return;
                            }
                            if (result.magnet && packs.length < 3) {
                                packs.push(result.magnet);
                            }
                        });
                        if (!packs.length) {
                            finish(found);
                            return;
                        }
                        var left = packs.length;
                        packs.forEach(function (packMagnet) {
                            post("/api/magnet_files/", { magnet_link: packMagnet }, function (info) {
                                var packHash = info && info.magnet_hash;
                                if (!packHash) {
                                    left -= 1;
                                    if (left === 0) {
                                        finish(found);
                                    }
                                    return;
                                }
                                var settled = false;
                                function settle(files) {
                                    if (settled) {
                                        return;
                                    }
                                    settled = true;
                                    episodesFromNames(files, signature, packMagnet, currentFile).forEach(function (episode) {
                                        addReleaseEpisode(found, episode);
                                    });
                                    left -= 1;
                                    if (left === 0) {
                                        finish(found);
                                    }
                                }
                                var source = subscribe("/api/magnet_events/" + packHash + "/", function (payload) {
                                    if (payload && payload.files) {
                                        settle(payload.files);
                                    }
                                }, function () {
                                    get("/api/magnet/" + packHash + "/", function (payload) {
                                        settle(payload && payload.files);
                                    });
                                });
                                setTimeout(function () {
                                    if (source && source.close) {
                                        source.close();
                                    }
                                    settle([]);
                                }, 8000);
                            });
                        });
                    });
                });
            },
            playEpisode: function (episode) {
                if (!episode || episode.current) {
                    this.openMenu = "";
                    return;
                }
                rememberEpisodeTarget(episode.season, episode.episode);
                var path = "";
                if (episode.filename && episode.magnet) {
                    path = "/magnet/" + encodeURIComponent(encodeURIComponent(episode.magnet)) + "/" + encodeURIComponent(episode.filename);
                } else if (episode.magnet) {
                    path = "/magnet/" + encodeURIComponent(encodeURIComponent(episode.magnet));
                } else if (episode.torrentLink) {
                    path = "/torrent/" + encodeURIComponent(episode.torrentLink);
                }
                if (!path) {
                    return;
                }
                this.openMenu = "";
                navigate("/", true);
                rbsetTimeout(function () {
                    navigate(path, true);
                });
            },
            placeCues: function (raised) {
                var video = this.videoEl();
                if (!video) {
                    return;
                }
                for (var i = 0; i < video.textTracks.length; i++) {
                    var cues = video.textTracks[i].cues;
                    if (!cues) {
                        continue;
                    }
                    for (var j = 0; j < cues.length; j++) {
                        var cue = cues[j];
                        if (!cue._rapidbayPlaced) {
                            cue._rapidbayLine = cue.line;
                            cue._rapidbaySnap = cue.snapToLines;
                            cue._rapidbayAlign = cue.lineAlign;
                            cue._rapidbayPlaced = true;
                        }
                        if (raised) {
                            cue.snapToLines = false;
                            cue.lineAlign = "end";
                            cue.line = 78;
                        } else {
                            cue.line = cue._rapidbayLine;
                            cue.snapToLines = cue._rapidbaySnap;
                            cue.lineAlign = cue._rapidbayAlign;
                        }
                    }
                }
            },
            refreshTracks: function () {
                var video = this.videoEl();
                if (!video) {
                    return;
                }
                var captions = [];
                var activeCaption = null;
                for (var i = 0; i < video.textTracks.length; i++) {
                    var track = video.textTracks[i];
                    if (track.kind !== "subtitles" && track.kind !== "captions") {
                        continue;
                    }
                    captions.push({
                        index: i,
                        label: languageName(track.language || track.label) || ("Track " + (captions.length + 1)),
                    });
                    if (track.mode === "showing") {
                        activeCaption = i;
                    }
                }
                this.captionChoices = captions;
                this.activeCaption = activeCaption;
                var audios = [];
                var activeAudio = null;
                if (video.audioTracks) {
                    for (var j = 0; j < video.audioTracks.length; j++) {
                        var audio = video.audioTracks[j];
                        audios.push({
                            index: j,
                            label: languageName(audio.language || audio.label) || ("Track " + (j + 1)),
                        });
                        if (audio.enabled) {
                            activeAudio = j;
                        }
                    }
                }
                this.audioChoices = audios;
                this.activeAudio = activeAudio;
            },
            selectCaption: function (index) {
                var video = this.videoEl();
                if (!video) {
                    return;
                }
                var chosen = null;
                for (var i = 0; i < video.textTracks.length; i++) {
                    var track = video.textTracks[i];
                    var on = index !== null && i === index;
                    track.mode = on ? "showing" : "disabled";
                    if (on) {
                        chosen = track.language || track.label || "";
                    }
                }
                if (chosen) {
                    localStorage.setItem("captionLanguage", chosen);
                } else {
                    localStorage.removeItem("captionLanguage");
                }
                this.refreshTracks();
            },
            selectAudio: function (index) {
                var video = this.videoEl();
                if (!video || !video.audioTracks) {
                    return;
                }
                for (var i = 0; i < video.audioTracks.length; i++) {
                    video.audioTracks[i].enabled = i === index;
                }
                this.refreshTracks();
            },
            playNext: function () {
                if (!this.nextFilename) {
                    return;
                }
                var magnet = this.nextMagnet || decodeURIComponent(decodeURIComponent(location.pathname.split("/")[2]));
                var nextPath = "/magnet/" + encodeURIComponent(encodeURIComponent(magnet)) + "/" + encodeURIComponent(this.nextFilename);
                navigate("/", true);
                rbsetTimeout(function () {
                    navigate(nextPath, true);
                });
            },
            toggleFullscreen: function () {
                if (!document.fullscreenElement && !document.mozFullScreenElement && !document.webkitFullscreenElement) {
                    var root = document.documentElement;
                    if (root.requestFullscreen) {
                        root.requestFullscreen();
                    } else if (root.mozRequestFullScreen) {
                        root.mozRequestFullScreen();
                    } else if (root.webkitRequestFullscreen) {
                        root.webkitRequestFullscreen(Element.ALLOW_KEYBOARD_INPUT);
                    }
                } else if (document.exitFullscreen) {
                    document.exitFullscreen();
                } else if (document.mozCancelFullScreen) {
                    document.mozCancelFullScreen();
                } else if (document.webkitCancelFullScreen) {
                    document.webkitCancelFullScreen();
                }
            },
        },
        mounted: function () {
            var magnet_hash = this.url.split("/")[2];
            var filename = (function (l) {
                return decodeURIComponent(l[l.length - 1]);
            })(location.pathname.split("/"));
            var self = this;

            function getNextFile() {
                return new Promise(function (resolve) {
                    get(
                        "/api/next_file/" + magnet_hash + "/" + filename,
                        function (data) {
                            resolve(data);
                        }
                    );
                });
            }

            var video = document.getElementsByTagName("video")[0];
            var videoUrl = window.location.origin + self.url;
            var isHLS = self.url.indexOf(".m3u8") !== -1;
            var savedPosition = getVideoPosition(self.magnet, self.filename);

            if (isHLS && typeof Hls !== "undefined" && Hls.isSupported()) {
                var errorRecoveries = 0;
                var maxRecoveries = 5;
                self.hls = new Hls({
                    // Resume through hls.js itself: setting video.currentTime
                    // before the manifest is parsed races hls.js's own initial
                    // seek (whose default for EVENT playlists is the live
                    // edge). 0 = explicit start-at-beginning.
                    startPosition: savedPosition > 0 ? savedPosition : 0,
                    maxBufferHole: 0.5,
                    nudgeOffset: 0.2,
                    nudgeMaxRetry: 10,
                    // Subtitles are exposed via EXT-X-MEDIA in the master
                    // playlist; suppress hls.js's CEA-608/708 auto-extraction
                    // so embedded closed captions don't render alongside.
                    enableCEA708Captions: false,
                });
                self.hls.on(Hls.Events.ERROR, function (event, data) {
                    if (!self.hls) return;
                    if (data.fatal) {
                        console.warn("HLS fatal error:", data.type, data.details);
                        errorRecoveries++;
                        if (errorRecoveries > maxRecoveries) {
                            self.hls.destroy();
                            self.hls = null;
                            if (self.onStreamError) {
                                self.onStreamError();
                            }
                            return;
                        }
                        if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
                            self.hls.recoverMediaError();
                        } else if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
                            self.hls.startLoad();
                        } else {
                            self.hls.destroy();
                            self.hls = null;
                            if (self.onStreamError) {
                                self.onStreamError();
                            }
                        }
                    }
                });
                self.hls.loadSource(videoUrl);
                self.hls.attachMedia(video);
            } else if (isHLS && video.canPlayType("application/vnd.apple.mpegurl")) {
                video.src = videoUrl;
            } else {
                video.src = videoUrl;
            }

            function rememberNext(data) {
                if (data && data.next_filename) {
                    self.nextFilename = data.next_filename;
                    self.nextMagnet = data.next_magnet || null;
                }
            }
            video.addEventListener("play", function () {
                self.syncPlayback();
                getNextFile().then(function (data) {
                    rememberNext(data);
                    if (data.next_filename) {
                        var magnet = data.next_magnet || decodeURIComponent(
                            decodeURIComponent(location.pathname.split("/")[2])
                        );
                        post("/api/magnet_download/", {
                            magnet_link: magnet,
                            filename: data.next_filename,
                        });
                    }
                });
            });
            getNextFile().then(rememberNext);
            ["pause", "timeupdate", "volumechange", "loadedmetadata", "durationchange"].forEach(function (eventName) {
                video.addEventListener(eventName, function () {
                    self.syncPlayback();
                    if (eventName === "loadedmetadata") {
                        self.refreshTracks();
                    }
                });
            });
            function bindCueLift(track) {
                if (!track || track._rapidbayCueLift) {
                    return;
                }
                track._rapidbayCueLift = true;
                track.addEventListener("cuechange", function () {
                    self.placeCues(self.controlsOn);
                });
            }
            for (var trackIndex = 0; trackIndex < video.textTracks.length; trackIndex++) {
                bindCueLift(video.textTracks[trackIndex]);
            }
            if (video.textTracks && video.textTracks.addEventListener) {
                video.textTracks.addEventListener("addtrack", function (event) {
                    bindCueLift(event.track);
                    self.refreshTracks();
                    self.placeCues(self.controlsOn);
                });
            }
            if (video.audioTracks && video.audioTracks.addEventListener) {
                video.audioTracks.addEventListener("addtrack", function () {
                    self.refreshTracks();
                });
            }

            video.addEventListener("ended", function () {
                getNextFile().then(function (data) {
                    if (data.next_filename) {
                        var magnet = data.next_magnet || decodeURIComponent(
                            decodeURIComponent(location.pathname.split("/")[2])
                        );
                        var next_path = "/magnet/" + encodeURIComponent(encodeURIComponent(magnet)) + "/" + encodeURIComponent(data.next_filename);
                        navigate("/", true);
                        rbsetTimeout(function () {
                            navigate(next_path, true);
                        });
                    }
                });
            });
            video.play();

            // Restore saved position (the hls.js path resumes via the
            // startPosition config above instead).
            if (savedPosition > 0 && !self.hls) {
                video.currentTime = savedPosition;
            }

            // Save position periodically and report unfinished plays for Keep watching.
            self.positionInterval = setInterval(function () {
                if (!video.paused && video.currentTime > 0) {
                    saveVideoPosition(self.magnet, self.filename, video.currentTime, video.duration);
                    reportPlaybackProgress(self.magnet, self.filename, video.currentTime, video.duration, false);
                }
            }, 5000);

            // Save position on pause
            video.addEventListener("pause", function () {
                saveVideoPosition(self.magnet, self.filename, video.currentTime, video.duration);
                reportPlaybackProgress(self.magnet, self.filename, video.currentTime, video.duration, true);
            });

            // Credits usually start before the file ends. Count the title as
            // watched at 98% or with under two minutes left, whichever comes first.
            var notedWatch = false;
            function noteWatched() {
                if (notedWatch) {
                    return;
                }
                notedWatch = true;
                clearVideoPosition(self.magnet, self.filename);
                markFileCompleted(self.magnet, self.filename);
            }
            function playbackCountsAsWatched() {
                return progressCountsAsWatched(video.currentTime, video.duration);
            }
            video.addEventListener("timeupdate", function () {
                if (playbackCountsAsWatched()) {
                    noteWatched();
                }
            });
            video.addEventListener("ended", noteWatched);

            function normalizeLanguage(lang) {
                return lang ? lang.split("-")[0].toLowerCase() : lang;
            }
            function applyCaptionPreference() {
                var tracks = video.textTracks;
                var captionLanguage = normalizeLanguage(localStorage.getItem("captionLanguage"));
                if (!captionLanguage) return;
                // Don't mutate modes unless we're actually selecting one — hls.js's
                // text-track poll treats any non-"disabled" track as the active
                // subtitle, so blanket-hiding tracks would auto-select whichever
                // happens to be last in the list.
                var hasShowing = false;
                var currentTrack;
                for (var i = 0; i < tracks.length; i++) {
                    if (tracks[i].mode === "showing") {
                        hasShowing = true;
                    }
                    if (!currentTrack && normalizeLanguage(tracks[i].language) === captionLanguage) {
                        currentTrack = tracks[i];
                    }
                }
                if (hasShowing || !currentTrack) return;
                currentTrack.mode = "showing";
            }
            var tracks = video.textTracks;
            for (var i = 0; i < tracks.length; i++) {
                var track = tracks[i];
                track.mode = "disabled";
            }
            applyCaptionPreference();
            this.addTrackListener = function () {
                applyCaptionPreference();
            };
            video.textTracks.addEventListener("addtrack", this.addTrackListener);
            this.captionChangeListener = function (e) {
                var tracks = e.currentTarget;
                // Multiple tracks can end up in "showing" simultaneously:
                // Chromium has had long-standing quirks where it auto-enables
                // every <track srclang="en"> that matches the user's caption
                // language, and hls.js's loadSource appends new TextTrack
                // objects without being able to remove the previously-shown
                // ones (HTML5 doesn't expose removal). When that happens the
                // user sees every line rendered twice. Keep the most-recently
                // activated track (highest index — newest from loadSource,
                // and matches the just-clicked one when flipCaptions cycles
                // forward) and hide the rest.
                var lastShowingIndex = -1;
                for (var i = 0; i < tracks.length; i++) {
                    if (tracks[i].mode === "showing") {
                        lastShowingIndex = i;
                    }
                }
                var captionLanguage = null;
                for (var j = 0; j < tracks.length; j++) {
                    if (tracks[j].mode !== "showing") continue;
                    if (j !== lastShowingIndex) {
                        // Setting mode re-fires "change", but the next pass
                        // sees only one showing and exits without further
                        // mutation — no infinite loop.
                        tracks[j].mode = "hidden";
                    } else {
                        captionLanguage = tracks[j].language;
                    }
                }
                if (captionLanguage) {
                    window.localStorage.setItem(
                        "captionLanguage",
                        normalizeLanguage(captionLanguage)
                    );
                } else {
                    window.localStorage.removeItem("captionLanguage");
                }
            };

            video.textTracks.addEventListener(
                "change",
                this.captionChangeListener
            );
            this.refreshTracks();

            this.videokeylistener = function (event) {
                const videoSelected =
                    ["video", "body"].indexOf(
                        document.activeElement &&
                            document.activeElement.tagName.toLowerCase()
                    ) !== -1;
                if (event.key.toLowerCase() === "arrowright" && videoSelected) {
                    event.preventDefault();
                    event.stopPropagation();
                    video.currentTime += 60;
                } else if (
                    event.key.toLowerCase() === "arrowleft" &&
                    videoSelected
                ) {
                    event.preventDefault();
                    event.stopPropagation();
                    video.currentTime -= 15;
                } else if (
                    event.key.toLowerCase() === "enter" &&
                    videoSelected
                ) {
                    event.preventDefault();
                    event.stopPropagation();
                    if (!video.paused) {
                        video.pause();
                    } else {
                        video.play();
                    }
                } else if (
                    event.key.toLowerCase() === "mediarewind" &&
                    videoSelected
                ) {
                    location.href = document.querySelector("video").src;
                }
            };

            document.addEventListener("keydown", this.videokeylistener, true);
        },

        created: function () {
            var timeout;
            var duration = 2800;
            var self = this;
            var lastCall = 0;
            this.mousemove_listener = function () {
                var now = Date.now();
                // Debounce: ignore if called within 100ms
                if (now - lastCall < 100) return;
                lastCall = now;
                self.hovering = true;
                clearTimeout(timeout);
                timeout = setTimeout(function () {
                    if (self.openMenu) {
                        return;
                    }
                    self.hovering = false;
                    // Blur video to prevent focus-related events
                    var video = document.querySelector("video");
                    if (video) video.blur();
                }, duration);
            };
            this.mousemove_listener();
            document.addEventListener("mousemove", this.mousemove_listener);
            document.addEventListener("touchstart", this.mousemove_listener);
            document.addEventListener("click", this.mousemove_listener);
            document.addEventListener("keydown", this.mousemove_listener);
        },
        destroyed: function () {
            document.removeEventListener("mousemove", this.mousemove_listener);
            document.removeEventListener("touchstart", this.mousemove_listener);
            document.removeEventListener("click", this.mousemove_listener);
            document.removeEventListener("keydown", this.mousemove_listener);
            document.removeEventListener(
                "keydown",
                this.videokeylistener,
                true
            );
            document.removeEventListener("keydown", this.keylistener);
            if (this.positionInterval) {
                clearInterval(this.positionInterval);
            }
            if (this.hls) {
                this.hls.destroy();
                this.hls = null;
            }
            var video = document.getElementsByTagName("video")[0];
            if (video) {
                video.textTracks.removeEventListener(
                    "change",
                    this.captionChangeListener
                );
                video.textTracks.removeEventListener(
                    "addtrack",
                    this.addTrackListener
                );
                if (video.currentTime > 0 && !progressCountsAsWatched(video.currentTime, video.duration)) {
                    saveVideoPosition(this.magnet, this.filename, video.currentTime, video.duration);
                    reportPlaybackProgress(this.magnet, this.filename, video.currentTime, video.duration, true);
                }
            }
        },
        template: "#player-template",
    });

    Vue.component("fullscreen-button", {
        template: "#fullscreen-button-template",
        methods: {
            toggleFullscreen: function () {
                if (
                    !document.fullscreenElement && // alternative standard method
                    !document.mozFullScreenElement &&
                    !document.webkitFullscreenElement
                ) {
                    // current working methods
                    if (document.documentElement.requestFullscreen) {
                        document.documentElement.requestFullscreen();
                    } else if (document.documentElement.mozRequestFullScreen) {
                        document.documentElement.mozRequestFullScreen();
                    } else if (
                        document.documentElement.webkitRequestFullscreen
                    ) {
                        document.documentElement.webkitRequestFullscreen(
                            Element.ALLOW_KEYBOARD_INPUT
                        );
                    }
                } else {
                    if (document.cancelFullScreen) {
                        document.cancelFullScreen();
                    } else if (document.mozCancelFullScreen) {
                        document.mozCancelFullScreen();
                    } else if (document.webkitCancelFullScreen) {
                        document.webkitCancelFullScreen();
                    }
                }
            },
        },
    });

    Vue.component("caption-button", {
        template: "#caption-button-template",
        data: function () {
            return { currentCaption: null, trackCount: 0 };
        },
        methods: {
            flipCaptions: function () {
                var video = document.getElementsByTagName("video")[0];
                var currentIndex = null;
                var tracks = video.textTracks;
                // Ensure all tracks are at least "hidden" so they load content
                for (var i = 0; i < tracks.length; i++) {
                    var track = tracks[i];
                    if (track.mode === "showing") {
                        currentIndex = i;
                    } else if (track.mode === "disabled") {
                        track.mode = "hidden";
                    }
                }
                if (currentIndex !== null) {
                    tracks[currentIndex].mode = "hidden";
                    if (tracks[currentIndex + 1]) {
                        tracks[currentIndex + 1].mode = "showing";
                        this.currentCaption = tracks[currentIndex + 1].language;
                    } else {
                        this.currentCaption = null;
                    }
                } else if (tracks.length > 0) {
                    tracks[0].mode = "showing";
                    this.currentCaption = tracks[0].language;
                }
            },
        },
        mounted: function () {
            var video = document.getElementsByTagName("video")[0];
            var self = this;
            if (!video) return;
            // TextTrackList is a live, non-plain object — Vue 2 can't observe
            // its length, and the `change` event only fires on mode changes,
            // not on track additions. With HLS, subtitle tracks are appended
            // by hls.js after mount, so we have to mirror the count into a
            // reactive data field and listen to `addtrack`/`removetrack`.
            self.trackCount = video.textTracks.length;
            for (var i = 0; i < video.textTracks.length; i++) {
                if (video.textTracks[i].mode === "showing") {
                    self.currentCaption = video.textTracks[i].language;
                }
            }
            this.captionChangeListener = function () {
                self.currentCaption = null;
                for (var i = 0; i < video.textTracks.length; i++) {
                    if (video.textTracks[i].mode === "showing") {
                        self.currentCaption = video.textTracks[i].language;
                    }
                }
            };
            this.trackListMutationListener = function () {
                self.trackCount = video.textTracks.length;
            };
            video.textTracks.addEventListener("change", this.captionChangeListener);
            video.textTracks.addEventListener("addtrack", this.trackListMutationListener);
            video.textTracks.addEventListener("removetrack", this.trackListMutationListener);
        },
        destroyed: function () {
            var video = document.getElementsByTagName("video")[0];
            if (!video) return;
            video.textTracks.removeEventListener("change", this.captionChangeListener);
            video.textTracks.removeEventListener("addtrack", this.trackListMutationListener);
            video.textTracks.removeEventListener("removetrack", this.trackListMutationListener);
        },
    });

    Vue.component("chromecast-button", {
        template: "#chromecast-button-template",
        props: ["videoUrl"],
        methods: {
            cast: function () {
                var root = window.location.origin;
                var video = document.getElementsByTagName("video")[0];
                var current_subtitle = null;
                if (video.plyr) {
                    if (current_subtitle && current_subtitle.active) {
                        current_subtitle = video.plyr.captions.currentTrackNode;
                    }
                } else {
                    var subtitle_tracks = Array.from(video.textTracks);
                    current_subtitle = subtitle_tracks.find(function (t) {
                        return t.mode !== "disabled" && t.mode !== "hidden";
                    });
                }
                var current_subtitle_url = current_subtitle
                    ? root + current_subtitle.id
                    : null;
                var contentUrl = this.videoUrl ? root + this.videoUrl : video.src;
                var media = {
                    content: contentUrl,
                    title: "RapidBay",
                    subtitles: current_subtitle
                        ? [
                              {
                                  active: true,
                                  src: current_subtitle_url,
                              },
                          ]
                        : [],
                };
                var cc = new ChromecastJS();
                cc.cast(media);
            },
        },
    });

    Vue.component("favorite-button", {
        template: "#favorite-button-template",
        props: ["magnet", "filename"],
        data: function () {
            return { isFavorited: false };
        },
        created: function () {
            this.checkFavorited();
        },
        methods: {
            checkFavorited: function () {
                var favorites = getFavorites();
                var magnetHash = get_hash(this.magnet);
                var filename = this.filename;
                this.isFavorited = favorites.some(function (f) {
                    return get_hash(f.magnet) === magnetHash && f.filename === filename;
                });
            },
            toggle: function () {
                if (this.isFavorited) {
                    removeFavorite(this.magnet, this.filename);
                } else {
                    saveFavorite(this.magnet, this.filename);
                }
                this.isFavorited = !this.isFavorited;
            },
        },
    });

    function rankMark(width, d, fade, opacity) {
        return {
            w: width,
            h: 148,
            paths: [{ d: d, fill: true }],
            x1: fade.x1,
            y1: fade.y1,
            x2: fade.x2,
            y2: fade.y2,
            opacity: opacity,
        };
    }
    var RANK_MARKS = {
        1: rankMark(85, "M29.75 47.0104V13.6887L86.59 0.138672V148.139H47.1763V42.4542L29.75 47.0104ZM49.4806 39.5094V145.875H84.2857V3.01729L32.0543 15.4686V44.0655L49.4806 39.5094Z", { x1: 50.0996, y1: 57.7836, x2: 85.0824, y2: 57.7836 }, 0.5),
        2: rankMark(85, "M110.771 23.6005C106.244 16.6041 99.9332 11.1854 91.8394 7.34424C83.7456 3.50309 74.5543 1.58252 64.2655 1.58252C53.9767 1.58252 44.854 3.57168 36.8973 7.55001C28.9407 11.5283 22.493 17.0157 17.5544 24.0121C13.1833 30.3814 10.3471 37.5466 9.04575 45.5077C8.91765 46.2914 8.80441 47.0829 8.70605 47.882H44.9226C45.8829 44.3153 47.872 41.3658 50.8901 39.0337C53.9081 36.5644 58.0236 35.3297 63.2366 35.3297C68.4496 35.3297 72.3593 36.633 74.9658 39.2395C77.7095 41.8459 79.0813 45.0698 79.0813 48.9109C79.0813 52.4777 78.0524 55.7015 75.9947 58.5824C74.0741 61.4632 70.5759 65.0986 65.5001 69.4885L10.3523 117.228V148.095H118.796V115.582H62.4135L90.6048 92.7411C95.5434 88.7628 100.07 84.5787 104.186 80.1888C108.301 75.7989 111.594 70.9975 114.063 65.7845C116.532 60.5715 117.767 54.6726 117.767 48.0878C117.767 38.7593 115.435 30.5969 110.771 23.6005ZM116.422 117.957H55.7114L89.1153 90.8921C93.9724 86.9794 98.4177 82.87 102.454 78.5649C106.408 74.347 109.558 69.7489 111.917 64.7681C114.216 59.915 115.393 54.3709 115.393 48.0878C115.393 39.1748 113.171 31.4818 108.795 24.9176L108.786 24.904L108.777 24.8904C104.508 18.292 98.5481 13.1562 90.8214 9.48927C83.0898 5.82 74.2544 3.95685 64.2655 3.95685C54.2875 3.95685 45.5381 5.88422 37.9591 9.67368C30.3437 13.4814 24.2058 18.7109 19.5032 25.3685C15.415 31.3296 12.7273 38.0322 11.4529 45.5077H43.1925C44.4252 42.2094 46.5138 39.4217 49.4124 37.1749C52.9756 34.2718 57.6742 32.9554 63.2366 32.9554C68.803 32.9554 73.4151 34.3454 76.623 37.5389C79.832 40.5978 81.4557 44.4401 81.4557 48.9109C81.4557 52.9557 80.2819 56.6521 77.9491 59.9311C75.8419 63.0803 72.1524 66.8743 67.0533 71.2843L12.7266 118.313V145.72H116.422V117.957Z", { x1: 48.4733, y1: 58.6615, x2: 83.0862, y2: 58.6615 }, 0.45),
        3: rankMark(85, "M50.3739 112.913C46.9032 111.178 44.6338 108.709 43.5659 105.505H7.12305C7.23052 106.307 7.35336 107.098 7.49156 107.879C9.58478 119.708 15.202 129.128 24.3433 136.141C34.0881 143.616 47.1701 147.354 63.5895 147.354C74.0017 147.354 83.2125 145.619 91.222 142.148C99.3649 138.677 105.706 133.805 110.244 127.531C114.917 121.123 117.253 113.514 117.253 104.704C117.253 97.7623 115.317 91.2213 111.446 85.0807C108.128 79.8177 103.29 75.8785 96.9317 73.2632C95.8717 72.8271 94.7693 72.4279 93.6248 72.0654C94.7469 71.639 95.8237 71.1768 96.8553 70.6787C101.96 68.2141 105.955 64.8718 108.843 60.652C112.313 55.4459 114.049 49.639 114.049 43.2315C114.049 34.8216 111.779 27.5464 107.241 21.4058C102.702 15.1318 96.6283 10.2594 89.0194 6.78863C81.4104 3.31789 73.0005 1.58252 63.7897 1.58252C48.5718 1.58252 36.2239 5.32025 26.7461 12.7957C17.8739 19.7935 11.9261 29.0138 8.90271 40.4567C8.69634 41.2378 8.50359 42.0292 8.32446 42.831H43.5659C44.5003 40.1612 46.5027 37.9586 49.573 36.2233C52.6433 34.4879 56.381 33.6202 60.7862 33.6202C65.7253 33.6202 69.73 34.6214 72.8003 36.6237C75.8706 38.4926 77.4057 41.4961 77.4057 45.6343C77.4057 49.3721 75.8706 52.5091 72.8003 55.0454C69.8635 57.4482 65.9255 58.6496 60.9864 58.6496H44.5671V89.2857H62.388C67.3272 89.2857 71.3986 90.3536 74.6024 92.4894C77.9397 94.6253 79.6083 97.7623 79.6083 101.901C79.6083 106.706 78.0064 110.177 74.8026 112.313C71.7324 114.315 67.7277 115.316 62.7885 115.316C58.1164 115.316 53.9782 114.515 50.3739 112.913ZM46.9414 86.9113H62.388C67.6555 86.9113 72.2137 88.0497 75.9011 90.5016C79.9435 93.0968 81.9826 97.0036 81.9826 101.901C81.9826 107.277 80.1504 111.601 76.1197 114.288L76.1097 114.295L76.0997 114.302C72.531 116.629 68.0323 117.691 62.7885 117.691C57.8446 117.691 53.3682 116.843 49.4096 115.083L49.3603 115.061L49.3121 115.037C45.938 113.35 43.4311 110.969 41.9652 107.879H9.90441C11.9566 118.965 17.2547 127.71 25.7885 134.257C34.9984 141.322 47.5176 144.98 63.5895 144.98C73.7385 144.98 82.6182 143.288 90.2779 139.969L90.2844 139.966L90.291 139.964C98.095 136.637 104.069 132.016 108.321 126.139L108.326 126.132C112.669 120.175 114.878 113.07 114.878 104.704C114.878 98.2315 113.081 92.1266 109.437 86.347C105.911 80.7543 100.471 76.7241 92.908 74.329L86.4039 72.2693L92.7814 69.8459C99.0729 67.4552 103.72 63.9282 106.875 59.3232C110.074 54.52 111.674 49.1774 111.674 43.2315C111.674 35.2754 109.537 28.5075 105.331 22.8171L105.324 22.8073L105.317 22.7975C101.038 16.883 95.2998 12.263 88.034 8.94885C80.7645 5.63296 72.6953 3.95685 63.7897 3.95685C48.9637 3.95685 37.1763 7.59306 28.2165 14.66C19.9305 21.1954 14.3092 29.7625 11.3619 40.4567H42.0064C43.3326 37.8682 45.5285 35.7819 48.4047 34.1562C51.9098 32.1751 56.0722 31.2459 60.7862 31.2459C66.015 31.2459 70.5029 32.3015 74.0667 34.615C77.9412 36.9883 79.78 40.8291 79.78 45.6343C79.78 50.1317 77.8878 53.9223 74.3125 56.8759L74.3081 56.8795L74.3038 56.883C70.8292 59.7259 66.3063 61.024 60.9864 61.024H46.9414V86.9113Z", { x1: 53.4701, y1: 57.0913, x2: 88.7906, y2: 57.0913 }, 0.4),
        4: rankMark(85, "M108.314 117.932H128.04V86.7518H108.314V0H69.7103L3.95703 88.2366V117.932H70.7708V147.627H108.314V117.932ZM105.939 145.252V115.557H125.665V89.1262H105.939V2.37433H70.902L6.33137 89.024V115.557H73.1451V145.252H105.939ZM37.186 89.1262L73.1451 41.0044V89.1262H37.186ZM70.7708 86.7518H41.9242L70.7708 48.1483V86.7518Z", { x1: 43.542, y1: 55.819, x2: 88.6544, y2: 55.819 }, 0.35),
        5: rankMark(85, "M49.1693 32.8877H110.365V0H18.3631L10.0371 88.88H44.1737C46.1165 86.521 48.6837 84.6477 51.8753 83.26C55.0669 81.8723 58.6055 81.1785 62.4909 81.1785C68.0416 81.1785 72.5515 82.7049 76.0207 85.7578C79.4899 88.8106 81.2244 92.9043 81.2244 98.0386C81.2244 103.312 79.4899 107.475 76.0207 110.528C72.5515 113.442 68.0416 114.899 62.4909 114.899C58.6055 114.899 55.1363 114.274 52.0834 113.025C49.0306 111.777 46.7409 110.111 45.2145 108.03H7.12305C7.31499 108.833 7.5212 109.624 7.74168 110.404C11.0278 122.033 17.4824 131.163 27.1054 137.795C37.5129 144.734 50.557 148.203 66.2376 148.203C76.2288 148.203 85.3181 146.26 93.5053 142.375C101.693 138.35 108.215 132.522 113.071 124.89C117.928 117.258 120.357 107.891 120.357 96.7897C120.357 87.6311 118.345 79.5133 114.32 72.4362C110.296 65.2203 104.745 59.6003 97.6683 55.576C90.7299 51.413 82.8896 49.3315 74.1473 49.3315C64.3385 49.3315 56.0463 52.0941 49.2709 57.6192C48.3781 58.3473 47.5116 59.1232 46.6715 59.9472L49.1693 32.8877ZM92.4728 140.236C100.265 136.403 106.45 130.872 111.068 123.615C115.633 116.442 117.982 107.542 117.982 96.7897C117.982 87.9902 116.053 80.2863 112.256 73.6098L112.251 73.6013L112.247 73.5927C108.43 66.7499 103.189 61.4464 96.4946 57.64L96.4705 57.6263L96.4467 57.612C89.907 53.6882 82.4952 51.7059 74.1473 51.7059C63.6007 51.7059 55.0604 55.0453 48.3341 61.6423L43.7122 66.1753L47.0041 30.5134H107.991V2.37433H20.5255L12.6443 86.5057H43.0956C45.196 84.2322 47.8248 82.432 50.9286 81.0826C54.4519 79.5507 58.3177 78.8042 62.4909 78.8042C68.4971 78.8042 73.603 80.4675 77.5892 83.9753C81.631 87.5321 83.5988 92.3067 83.5988 98.0386C83.5988 103.887 81.6457 108.74 77.5892 112.31L77.5687 112.328L77.5478 112.346C73.5607 115.695 68.4699 117.273 62.4909 117.273C58.3511 117.273 54.5687 116.607 51.1844 115.223C48.2813 114.035 45.8729 112.449 44.0792 110.404H10.2131C13.4078 121.212 19.4806 129.652 28.4379 135.83C38.3645 142.443 50.9147 145.828 66.2376 145.828C75.9072 145.828 84.6388 143.951 92.4728 140.236Z", { x1: 46.5993, y1: 54.6477, x2: 87.9395, y2: 54.6477 }, 0.3),
        6: rankMark(85, "M48.7154 39.7115C52.9026 34.4437 58.3056 31.8097 64.9241 31.8097C68.7062 31.8097 71.8129 32.4851 74.2442 33.8358C76.6755 35.0515 78.499 36.6048 79.7147 38.4959H117.197C116.99 37.6927 116.77 36.9012 116.538 36.1215C113.293 25.2317 107.638 16.6355 99.5704 10.3331C90.9257 3.44437 79.2419 0 64.5189 0C52.9026 0 42.5695 2.83654 33.5196 8.50961C24.6048 14.1827 17.581 22.4897 12.4482 33.4306C7.31542 44.3716 4.74902 57.6087 4.74902 73.1422C4.74902 87.1898 7.04527 99.8191 11.6378 111.03C16.2302 122.241 23.0514 131.156 32.1014 137.775C41.1513 144.258 52.3623 147.5 65.7346 147.5C72.4882 147.5 79.0393 146.419 85.3877 144.258C91.7362 142.097 97.4768 138.855 102.61 134.533C107.742 130.211 111.795 124.943 114.766 118.729C117.873 112.381 119.426 105.087 119.426 96.8475C119.426 88.0677 117.333 80.2335 113.145 73.3448C109.093 66.456 103.623 61.0531 96.7339 57.136C89.8452 53.2188 82.2811 51.2603 74.0416 51.2603C61.2346 51.2603 51.2382 54.8664 44.0524 62.0786C43.129 63.0054 42.252 63.9918 41.4214 65.0378C41.5171 63.6499 41.6354 62.3082 41.7764 61.0126C42.8287 51.3385 45.1417 44.2381 48.7154 39.7115ZM33.4936 135.851C24.8308 129.513 18.2735 120.965 13.8349 110.13C9.37654 99.2465 7.12336 86.9297 7.12336 73.1422C7.12336 57.8614 9.64893 44.9878 14.5977 34.439C19.566 23.8489 26.3081 15.9151 34.7873 10.5173C43.4247 5.10448 53.311 2.37433 64.5189 2.37433C78.8829 2.37433 89.9876 5.73279 98.0907 12.19L98.0997 12.1971L98.1087 12.2041C105.575 18.0371 110.906 25.9705 114.056 36.1215H80.9312C79.5073 34.3277 77.6202 32.876 75.3515 31.735C72.4716 30.1481 68.9494 29.4354 64.9241 29.4354C57.5677 29.4354 51.4856 32.4106 46.8567 38.2341L46.8518 38.2403C42.3484 43.9445 39.8731 52.9788 39.0527 64.8744L38.5267 72.5009L43.2808 66.5143C50.0203 58.0275 60.1275 53.6346 74.0416 53.6346C81.8866 53.6346 89.0437 55.4945 95.5602 59.2C102.085 62.9099 107.255 68.0148 111.099 74.5486L111.107 74.5634L111.116 74.578C115.058 81.0622 117.052 88.4626 117.052 96.8475C117.052 104.785 115.557 111.712 112.633 117.686L112.629 117.695L112.624 117.705C109.794 123.622 105.948 128.618 101.08 132.717C96.173 136.849 90.6915 139.945 84.6226 142.011C78.5223 144.087 72.2299 145.126 65.7346 145.126C52.7611 145.126 42.063 141.987 33.4936 135.851ZM79.0814 112.586L79.0634 112.602C74.9577 116.252 69.9976 118.065 64.3163 118.065C58.6356 118.065 53.6254 116.253 49.3989 112.63L49.3643 112.601L49.3309 112.57C45.181 108.727 43.0993 103.833 43.0993 98.0632C43.0993 92.294 45.1805 87.4001 49.3297 83.5577C53.548 79.6413 58.5811 77.6566 64.3163 77.6566C70.0461 77.6566 75.0232 79.6386 79.1162 83.5724C83.2548 87.4126 85.3308 92.3014 85.3308 98.0632C85.3308 103.833 83.2491 108.727 79.0991 112.57L79.0814 112.586ZM50.9441 85.2987C47.2971 88.6756 45.4736 92.9304 45.4736 98.0632C45.4736 103.196 47.2971 107.451 50.9441 110.828C54.7261 114.069 59.1835 115.69 64.3163 115.69C69.4491 115.69 73.839 114.069 77.486 110.828C81.1329 107.451 82.9564 103.196 82.9564 98.0632C82.9564 92.9304 81.1329 88.6756 77.486 85.2987C73.839 81.7868 69.4491 80.0309 64.3163 80.0309C59.1835 80.0309 54.7261 81.7868 50.9441 85.2987Z", { x1: 46.6534, y1: 56.4078, x2: 87.9935, y2: 56.4078 }, 0.3),
        7: rankMark(85, "M26.7605 147.316H68.2338L119.181 32.3702V0.791504H9.49756V34.4754H78.9706L26.7605 147.316ZM11.8719 32.1011H82.6853L30.4753 144.942H66.6891L116.806 31.8676V3.16584H11.8719V32.1011Z", { x1: 46.7831, y1: 56.3003, x2: 88.1232, y2: 56.3003 }, 0.3),
        8: rankMark(85, "M11.6378 85.0772C7.04527 91.2906 4.74902 98.1118 4.74902 105.541C4.74902 114.591 7.18034 122.29 12.043 128.638C16.9056 134.987 23.5917 139.849 32.1014 143.226C40.746 146.603 50.6064 148.291 61.6824 148.291C72.7584 148.291 82.5512 146.603 91.0608 143.226C99.7055 139.849 106.459 134.987 111.322 128.638C116.184 122.29 118.616 114.591 118.616 105.541C118.616 98.1118 116.32 91.2906 111.727 85.0772C107.775 79.6137 102.522 75.5008 95.9686 72.7384C94.9071 72.2909 93.8114 71.8789 92.6817 71.5023C93.8071 71.0855 94.8875 70.6365 95.9229 70.1554C101.598 67.5182 105.92 63.915 108.89 59.3457C112.537 53.8077 114.361 47.8645 114.361 41.5161C114.361 33.5468 112.2 26.5229 107.877 20.4447C103.555 14.3664 97.4093 9.57126 89.4399 6.05935C81.6057 2.54746 72.3532 0.791504 61.6824 0.791504C51.0116 0.791504 41.6916 2.54746 33.7222 6.05935C25.888 9.57126 19.8097 14.3664 15.4873 20.4447C11.165 26.5229 9.00383 33.5468 9.00383 41.5161C9.00383 47.8645 10.7598 53.8077 14.2717 59.3457C17.3564 63.9156 21.7455 67.5192 27.4393 70.1564C28.4772 70.6372 29.5585 71.0858 30.6831 71.5023C29.5529 71.8791 28.4569 72.2913 27.395 72.7389C20.8422 75.5013 15.5898 79.6141 11.6378 85.0772ZM16.2586 58.0453C12.9917 52.8828 11.3782 47.3879 11.3782 41.5161C11.3782 34.0042 13.4058 27.4689 17.4223 21.8206C21.4633 16.1381 27.1824 11.5942 34.6865 8.22907C42.2928 4.8785 51.272 3.16584 61.6824 3.16584C72.0974 3.16584 81.0046 4.88 88.4687 8.22596L88.4756 8.22903L88.4825 8.23207C96.1266 11.6007 101.907 16.146 105.942 21.8206C109.959 27.4689 111.987 34.0042 111.987 41.5161C111.987 47.379 110.311 52.8714 106.908 58.0399L106.904 58.0458L106.9 58.0518C103.72 62.9438 98.7738 66.714 91.857 69.2758L85.5271 71.6202L91.9309 73.7548C99.6086 76.3141 105.529 80.5597 109.803 86.4688L109.81 86.4787L109.818 86.4885C114.121 92.3108 116.241 98.6412 116.241 105.541C116.241 114.141 113.941 121.314 109.437 127.195C104.878 133.146 98.5034 137.77 90.1969 141.015L90.191 141.017L90.1851 141.019C82.006 144.265 72.5198 145.917 61.6824 145.917C50.8488 145.917 41.2917 144.266 32.9714 141.017C24.8049 137.775 18.4923 133.154 13.9279 127.195C9.42392 121.314 7.12336 114.141 7.12336 105.541C7.12336 98.6412 9.2437 92.3108 13.5471 86.4885L13.5544 86.4787L13.5615 86.4688C17.8362 80.5597 23.7561 76.3141 31.4339 73.7548L37.8377 71.6202L31.5077 69.2758C24.6003 66.7175 19.5775 62.9484 16.2586 58.0453ZM75.5201 56.9488L75.5154 56.9525C71.7719 59.9161 67.0997 61.3149 61.6824 61.3149C56.2616 61.3149 51.5442 59.9151 47.6839 56.9813L47.6415 56.9491L47.6006 56.9149C43.8224 53.7664 41.8836 49.6561 41.8836 44.7578C41.8836 39.6422 43.7854 35.4199 47.6418 32.3645C51.5028 29.2775 56.2357 27.7956 61.6824 27.7956C67.1086 27.7956 71.7834 29.2673 75.5208 32.3642C79.4942 35.4032 81.4812 39.6208 81.4812 44.7578C81.4812 49.6934 79.4435 53.8101 75.5248 56.945L75.5201 56.9488ZM49.1206 34.2221C45.8788 36.7885 44.2579 40.3004 44.2579 44.7578C44.2579 48.9451 45.8788 52.3895 49.1206 55.0909C52.4974 57.6573 56.6847 58.9405 61.6824 58.9405C66.6801 58.9405 70.7998 57.6573 74.0416 55.0909C77.4184 52.3895 79.1068 48.9451 79.1068 44.7578C79.1068 40.3004 77.4184 36.7885 74.0416 34.2221C70.7998 31.5207 66.6801 30.1699 61.6824 30.1699C56.6847 30.1699 52.4974 31.5207 49.1206 34.2221ZM47.7023 91.5607C51.4844 88.7242 56.1444 87.3059 61.6824 87.3059C67.2204 87.3059 71.8129 88.7242 75.4599 91.5607C79.2419 94.3972 81.1329 98.0442 81.1329 102.502C81.1329 107.094 79.2419 110.809 75.4599 113.645C71.8129 116.482 67.2204 117.9 61.6824 117.9C56.1444 117.9 51.4844 116.482 47.7023 113.645C44.0553 110.809 42.2318 107.094 42.2318 102.502C42.2318 98.0442 44.0553 94.3972 47.7023 91.5607ZM76.901 115.532C72.7619 118.745 67.6321 120.274 61.6824 120.274C55.7219 120.274 50.5382 118.74 46.2777 115.545L46.261 115.532L46.2446 115.519C42.0234 112.236 39.8575 107.832 39.8575 102.502C39.8575 97.2809 42.0439 92.9537 46.2446 89.6865L46.261 89.6737L46.2777 89.6612C50.5382 86.4659 55.7219 84.9316 61.6824 84.9316C67.6321 84.9316 72.7621 86.461 76.9011 89.6738C81.228 92.9256 83.5073 97.2523 83.5073 102.502C83.5073 107.86 81.2494 112.264 76.901 115.532Z", { x1: 46.6534, y1: 57.1993, x2: 87.9935, y2: 57.1993 }, 0.3),
        9: rankMark(85, "M89.4307 12.1787L89.4239 12.1738C81.0668 6.22254 70.4559 3.16584 57.4307 3.16584C50.868 3.16584 44.5047 4.25819 38.329 6.44446C32.3099 8.62265 26.8702 11.8223 21.9985 16.053C17.1548 20.2594 13.332 25.2905 10.5221 31.1658C7.74894 36.9642 6.33185 43.6412 6.33185 51.2493C6.33185 59.5762 8.24795 66.9231 12.0296 73.3557C15.8431 79.7082 20.9098 84.7096 27.253 88.3906C33.7074 92.0587 40.8683 93.905 48.7865 93.905C56.2067 93.905 62.3048 92.8631 67.1601 90.876C72.0127 88.7562 76.1171 85.5858 79.4935 81.3339L84.241 75.3556L83.7217 82.972C82.9082 94.9032 80.4542 103.943 75.9795 109.611L75.9699 109.623L75.9602 109.635C71.4741 115.168 65.4937 117.952 58.2348 117.952C54.1223 117.952 50.5298 117.317 47.5691 115.914C45.1488 114.768 43.1588 113.248 41.6994 111.318H8.82826C11.6754 121.189 17.2055 129.037 25.4389 134.954C34.6 141.441 46.2159 144.765 60.4461 144.765C78.0669 144.765 91.4055 138.777 100.804 126.965L100.809 126.959L100.814 126.953C110.39 115.079 115.364 97.4072 115.364 73.5632C115.364 59.8847 113.129 47.7378 108.711 37.0816L108.706 37.0702L108.701 37.0587C104.436 26.4598 98.0105 18.1973 89.4376 12.1835L89.4307 12.1787ZM6.36174 111.318C6.14757 110.538 5.94925 109.747 5.76676 108.944H42.9567C44.1629 110.954 46.0392 112.562 48.5855 113.769C51.1318 114.975 54.3483 115.578 58.2348 115.578C64.8017 115.578 70.0954 113.099 74.1159 108.14C77.6629 103.647 79.9582 96.5465 81.0018 86.8383C81.1412 85.5422 81.2582 84.1996 81.3529 82.8105C80.5193 83.8602 79.6431 84.8494 78.7242 85.7782C75.6541 88.8812 72.1078 91.3094 68.0851 93.0629C62.8584 95.2071 56.4256 96.2793 48.7865 96.2793C40.4774 96.2793 32.9054 94.336 26.0705 90.4495C19.3696 86.563 14.0089 81.2693 9.98833 74.5684C5.96779 67.7335 3.95752 59.9604 3.95752 51.2493C3.95752 43.3422 5.43172 36.3063 8.38011 30.1414C11.3285 23.9766 15.349 18.6829 20.4417 14.2603C25.5344 9.83771 31.2302 6.48726 37.529 4.20895C43.9619 1.93065 50.5958 0.791504 57.4307 0.791504C70.8325 0.791504 81.956 3.94092 90.8012 10.2398C99.7804 16.5386 106.481 25.1828 110.904 36.1722C115.46 47.1617 117.739 59.6254 117.739 73.5632C117.739 97.6865 112.713 115.98 102.662 128.444C92.7444 140.907 78.6725 147.139 60.4461 147.139C45.8381 147.139 33.7095 143.722 24.0602 136.887C15.1928 130.517 9.29327 121.994 6.36174 111.318ZM43.957 35.6362C48.0299 31.8649 52.9676 29.9784 58.6369 29.9784C64.3061 29.9784 69.2438 31.8649 73.3167 35.6362C77.4382 39.4524 79.5057 44.3135 79.5057 50.0431C79.5057 55.7727 77.4382 60.6338 73.3167 64.45C69.2438 68.2213 64.3061 70.1078 58.6369 70.1078C52.9676 70.1078 48.0299 68.2213 43.957 64.45C39.8355 60.6338 37.768 55.7727 37.768 50.0431C37.768 44.3135 39.8355 39.4524 43.957 35.6362ZM45.5701 37.3784C49.1886 34.028 53.5442 32.3527 58.6369 32.3527C63.7295 32.3527 68.0851 34.028 71.7036 37.3784C75.3221 40.7289 77.1313 44.9504 77.1313 50.0431C77.1313 55.1358 75.3221 59.3573 71.7036 62.7078C68.0851 66.0582 63.7295 67.7335 58.6369 67.7335C53.5442 67.7335 49.1886 66.0582 45.5701 62.7078C41.9516 59.3573 40.1424 55.1358 40.1424 50.0431C40.1424 44.9504 41.9516 40.7289 45.5701 37.3784Z", { x1: 46.7055, y1: 56.0723, x2: 88.0456, y2: 56.0723 }, 0.3),
        10: rankMark(88, "M96.75 0C108.672 0 119.044 3.02061 127.817 9.09961C136.705 15.167 143.484 23.7166 148.168 34.6982C152.986 45.5531 155.375 58.3723 155.375 73.125C155.375 87.8798 152.986 100.764 148.169 111.749C143.484 122.602 136.703 131.085 127.816 137.151C119.043 143.23 108.671 146.25 96.75 146.25C84.8266 146.25 74.3903 143.229 65.4883 137.153L65.4824 137.148C60.5209 133.71 56.1945 129.495 52.5 124.514V143.375H16.0146V42.8057L0 47.1436V15.2168L52.5 2.25195V21.7998C52.4556 21.8602 52.4114 21.9208 52.3672 21.9814C56.0902 16.8787 60.4606 12.5819 65.4824 9.10156L65.4883 9.09668C74.3903 3.02074 84.8266 6.44338e-07 96.75 0ZM96.75 2.25C85.2271 2.25 75.2463 5.16254 66.7607 10.9531C58.3937 16.7527 51.8667 24.9499 47.1973 35.5957C42.6619 46.1043 40.375 58.6041 40.375 73.125C40.375 87.6431 42.6611 100.209 47.1973 110.852C51.8653 121.363 58.3908 129.496 66.7598 135.297C75.2454 141.088 85.2269 144 96.75 144C108.275 144 118.188 141.086 126.539 135.299L126.545 135.295C135.045 129.493 141.568 121.362 146.104 110.855L146.106 110.849C150.773 100.208 153.125 87.6429 153.125 73.125C153.125 58.6064 150.773 46.1097 146.108 35.6035L146.105 35.5957L146.102 35.5879C141.565 24.9486 135.041 16.7542 126.545 10.9551L126.539 10.9512C118.188 5.16359 108.275 2.25 96.75 2.25ZM2.25 16.9785V44.2031L18.2646 39.8652V141.125H50.25V121.265C48.3529 118.329 46.6484 115.16 45.1377 111.758L45.1338 111.75L45.1309 111.742C40.4482 100.76 38.125 87.878 38.125 73.125C38.125 58.3726 40.448 45.5546 45.1328 34.7012L45.1357 34.6953C46.6469 31.2496 48.3517 28.0435 50.25 25.0781V5.125L2.25 16.9785ZM96.75 32.4395C103.715 32.4395 109.06 36.1892 112.764 43.3281C116.444 50.2903 118.228 60.2625 118.228 73.125C118.228 85.9921 116.443 96.0258 112.766 103.115L112.762 103.123C109.052 110.137 103.704 113.811 96.75 113.811C89.7955 113.811 84.4478 110.137 80.7383 103.123L80.7344 103.115C77.0572 96.0258 75.2725 85.9921 75.2725 73.125C75.2725 60.2625 77.0556 50.2903 80.7363 43.3281C84.4405 36.1892 89.7853 32.4395 96.75 32.4395ZM96.75 34.6895C90.8065 34.6895 86.1406 37.7955 82.7314 44.3682L82.7275 44.376C79.2962 50.8641 77.5225 60.4075 77.5225 73.125C77.5225 85.8378 79.2946 95.4514 82.7295 102.076C86.1331 108.509 90.7964 111.561 96.75 111.561C102.704 111.561 107.367 108.509 110.771 102.076C114.205 95.4514 115.978 85.8378 115.978 73.125C115.978 60.4075 114.204 50.8641 110.772 44.376L110.769 44.3682C107.359 37.7955 102.693 34.6895 96.75 34.6895Z", { x1: 0.25, y1: 55.3444, x2: 114.25, y2: 56.625 }, 0.3),
    };

    Vue.component("rank-mark", {
        template: "#rank-mark-template",
        props: ["rank", "uid"],
        computed: {
            art: function () {
                return RANK_MARKS[this.rank] || RANK_MARKS[1];
            },
            fadeId: function () {
                return "rank-fade-" + this.uid;
            },
            clipId: function () {
                return "rank-clip-" + this.uid;
            },
        },
    });

    Vue.component("search-screen", {
        template: "#search-screen-template",
        data: function () {
            return {
                searchterm: "",
                searchHistory: [],
                richContentEnabled: localStorage.getItem("richContentEnabled") === "true",
                keepWatching: [],
                recentTitles: [],
                topSeries: [],
                topMovies: [],
                homeRetried: false,
            };
        },
        methods: {
            onRichToggle: function () {
                localStorage.setItem("richContentEnabled", this.richContentEnabled ? "true" : "false");
                this.applyPageBackground();
            },
            applyPageBackground: function () {
                var color = this.richContentEnabled ? "#141414" : "#000";
                document.documentElement.style.backgroundColor = color;
                document.body.style.backgroundColor = color;
            },
            recentSubtitle: function (title) {
                if (!title || title.media_type !== "tv") {
                    return title && title.year ? String(title.year) : "";
                }
                var episodes = title.watched_episodes || [];
                var latest = null;
                episodes.forEach(function (episode) {
                    if (!latest || (episode.at || 0) >= (latest.at || 0)) {
                        latest = episode;
                    }
                });
                if (!latest) {
                    return "";
                }
                function pad(value) {
                    var number = parseInt(value, 10);
                    return (number < 10 ? "0" : "") + number;
                }
                return "S" + pad(latest.season) + "E" + pad(latest.episode);
            },
            cardSubtitle: function (title) {
                if (title && title.subtitle) {
                    return title.subtitle;
                }
                return this.recentSubtitle(title);
            },
            formatAirDate: function (value) {
                var match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value || "");
                if (!match) {
                    return value || "";
                }
                var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
                var month = months[parseInt(match[2], 10) - 1];
                if (!month) {
                    return value;
                }
                var day = parseInt(match[3], 10);
                if (match[1] === String(new Date().getFullYear())) {
                    return day + " " + month;
                }
                return day + " " + month + " " + match[1];
            },
            nudgeRow: function (event, direction) {
                var rail = event.currentTarget && event.currentTarget.parentNode;
                var scroller = rail && rail.querySelector(".billboard-scroller");
                if (!scroller) {
                    return;
                }
                var amount = Math.max(220, Math.round(scroller.clientWidth * 0.8));
                scroller.scrollBy({ left: direction * amount, behavior: "smooth" });
            },
            refreshRails: function () {
                var rails = document.querySelectorAll(".home-row-rail");
                Array.prototype.forEach.call(rails, function (rail) {
                    var scroller = rail.querySelector(".billboard-scroller");
                    var prev = rail.querySelector(".row-nudge-prev");
                    var next = rail.querySelector(".row-nudge-next");
                    if (!scroller || !prev || !next) {
                        return;
                    }
                    var max = scroller.scrollWidth - scroller.clientWidth;
                    prev.hidden = scroller.scrollLeft <= 2;
                    next.hidden = max <= 2 || scroller.scrollLeft >= max - 2;
                });
            },
            loadHome: function () {
                var self = this;
                get("/api/home/", function (data) {
                    self.keepWatching = data && data.keep_watching ? data.keep_watching : [];
                    self.recentTitles = data && data.recent ? data.recent : [];
                    self.topSeries = data && data.series ? data.series : [];
                    self.topMovies = data && data.movies ? data.movies : [];
                    self.$nextTick(function () {
                        var scrollers = document.querySelectorAll(".poster-scroller");
                        Array.prototype.forEach.call(scrollers, function (scroller) {
                            scroller.scrollLeft = 0;
                        });
                        self.refreshRails();
                    });
                    var missingArtwork = self.recentTitles.concat(self.topSeries, self.topMovies).some(function (item) {
                        return item && !item.backdrop_url;
                    });
                    if (missingArtwork && !self.homeRetried) {
                        self.homeRetried = true;
                        setTimeout(function () {
                            self.loadHome();
                        }, 2500);
                    }
                });
            },
            resumeTitle: function (title) {
                if (title && title.magnet && title.filename) {
                    navigate("/magnet/" + encodeURIComponent(encodeURIComponent(title.magnet)) + "/" + encodeURIComponent(title.filename));
                    return;
                }
                this.openTitle(title);
            },
            openTitle: function (title) {
                var term = title && title.title ? title.title : "";
                if (!term) {
                    return;
                }
                this.searchterm = term;
                saveSearchTerm(term);
                var path = "/search/" + term;
                if (title.tmdb_id && (title.media_type === "tv" || title.media_type === "movie")) {
                    path += "?media=" + title.media_type + "&tmdb=" + title.tmdb_id;
                }
                navigate(path);
            },
            onSubmit: function (e) {
                e.preventDefault();
                if (this.searchterm.startsWith("magnet:")) {
                    navigate(
                        "/magnet/" +
                            encodeURIComponent(
                                encodeURIComponent(this.searchterm)
                            )
                    );
                } else {
                    saveSearchTerm(this.searchterm);
                    navigate("/search/" + this.searchterm);
                }
            },
            onHistoryClick: function (term) {
                this.searchterm = term;
                saveSearchTerm(term);
                navigate("/search/" + term);
            },
            clearSearches: function () {
                clearSearchHistory();
                this.searchHistory = [];
            },
            goHistory: function () {
                navigate("/search/[history]");
            },
            goTrending: function () {
                navigate("/search/");
            },
            goFavorites: function () {
                navigate("/search/[favorites]");
            },
            goHome: function () {
                navigate("/");
            },
        },
        mounted: function () {
            this.applyPageBackground();
            this.searchHistory = getSearchHistory();
            syncLibraryFromLocalHistory();
            this.loadHome();
            var progressEvents = collectInProgressEvents();
            if (progressEvents.length) {
                reportLibraryEvents(progressEvents);
                var home = this;
                setTimeout(function () {
                    home.loadHome();
                }, 2500);
            }
            var self = this;
            this.onHomeResize = function () {
                self.refreshRails();
            };
            window.addEventListener("resize", this.onHomeResize);

            if (
                router.lastRouteResolved().url.toLowerCase() ===
                "/registerhandler"
            ) {
                navigator.registerProtocolHandler(
                    "magnet",
                    router.root + "/magnet/%s",
                    "RapidBay"
                );
            }

            this.keylistener = function (e) {
                var name = e.key;
                var lowername = name.toLowerCase();
                var isTopbarButton = document.activeElement && document.activeElement.classList.contains("home-shortcut");
                var isHistoryItem = document.activeElement && (document.activeElement.classList.contains("search-chip") || document.activeElement.classList.contains("search-history-item"));
                var isRecentItem = document.activeElement && (document.activeElement.classList.contains("billboard-card") || document.activeElement.classList.contains("poster-card") || document.activeElement.classList.contains("home-basic-item") || document.activeElement.classList.contains("search-chip") || document.activeElement.classList.contains("search-history-item") || document.activeElement.classList.contains("search-history-clear") || document.activeElement.classList.contains("home-shortcut") || document.activeElement.classList.contains("row-nudge"));
                var isHomeToggle = document.activeElement && document.activeElement.closest(".rich-toggle-label");
                var isSearchInput = document.activeElement && document.activeElement.classList.contains("form-control");
                var homeStops = document.querySelectorAll(".rich-toggle-label input, .billboard-card, .poster-card, .home-basic-item, .search-chip, .search-history-item, .search-history-clear, .home-shortcut, .row-nudge:not([hidden])");
                if (lowername === "enter" && !isSearchInput && (isTopbarButton || isHistoryItem || isRecentItem)) {
                    e.preventDefault();
                    document.activeElement.click();
                } else if (lowername === "arrowdown") {
                    if (isSearchInput) {
                        return;
                    }
                    e.preventDefault();
                    if (isHistoryItem || isRecentItem || isHomeToggle) {
                        focusNextElement();
                    } else {
                        $("input.form-control").focus().click();
                    }
                } else if (lowername === "arrowup") {
                    if (isSearchInput) {
                        return;
                    }
                    e.preventDefault();
                    if (isHistoryItem || isRecentItem || isHomeToggle) {
                        var idx = Array.prototype.indexOf.call(homeStops, document.activeElement);
                        if (idx <= 0) {
                            $("input.form-control").focus().click();
                        } else {
                            focusPrevElement();
                        }
                    } else if (!isTopbarButton) {
                        $(".topbar-home button:first").focus();
                    }
                } else if (lowername === "arrowright" && !isSearchInput) {
                    e.preventDefault();
                    focusNextElement();
                } else if (lowername === "arrowleft" && !isSearchInput) {
                    e.preventDefault();
                    focusPrevElement();
                }
            };

            document.addEventListener("keydown", this.keylistener);
        },
        updated: function () {
            this.refreshRails();
        },
        destroyed: function () {
            document.documentElement.style.backgroundColor = "";
            document.body.style.backgroundColor = "";
            document.removeEventListener("keydown", this.keylistener);
            window.removeEventListener("resize", this.onHomeResize);
        },
    });

    function flexibleShowPattern(showTitle) {
        var parts = String(showTitle || "").split(/[\s._:-]+/).filter(Boolean).map(function (part) {
            return part.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        });
        if (!parts.length) {
            return null;
        }
        return parts.join("[\\s._:-]+");
    }

    var RESOLUTION_LABELS = [
        { rank: 2160, label: "2160p", pattern: "2160p|4k|uhd" },
        { rank: 1080, label: "1080p", pattern: "1080p|full[\\s._-]*hd" },
        { rank: 720, label: "720p", pattern: "720p" },
        { rank: 576, label: "576p", pattern: "576p" },
        { rank: 480, label: "480p", pattern: "480p" },
    ];

    function stripKnownMovieTitle(title, movieTitle, year) {
        var cleaned = title;
        var showPattern = flexibleShowPattern(movieTitle);
        if (showPattern) {
            var part = "(?:[\\s._:-]+part[\\s._:-]*(?:one|two|three|four|1|2|3|4|i{1,3}))?";
            cleaned = cleaned.replace(new RegExp("(^|[^A-Za-z0-9])" + showPattern + part + "(?![A-Za-z0-9])", "ig"), "$1 ");
        }
        if (year) {
            cleaned = cleaned.replace(new RegExp("\\(\\s*" + year + "\\s*\\)", "g"), " ");
            cleaned = cleaned.replace(new RegExp("(^|[^0-9])" + year + "(?![0-9])", "g"), "$1 ");
        }
        cleaned = cleaned.replace(/[\[\]()]/g, " ");
        return cleaned.replace(/\s{2,}/g, " ").trim();
    }

    function labelWithResolution(title) {
        var cleaned = title;
        var rank = 0;
        var label = "";
        for (var i = 0; i < RESOLUTION_LABELS.length; i++) {
            var spec = RESOLUTION_LABELS[i];
            var found = new RegExp("(?:^|[^A-Za-z0-9])(?:" + spec.pattern + ")(?![A-Za-z0-9])", "i").test(cleaned);
            if (!found) {
                continue;
            }
            rank = spec.rank;
            label = spec.label;
            cleaned = cleaned.replace(new RegExp("(?:^|[^A-Za-z0-9])(?:" + spec.pattern + ")(?![A-Za-z0-9])", "ig"), " ");
            break;
        }
        cleaned = cleaned.replace(/^[\s._:-]+/, "").replace(/[\s._:-]+$/, "").replace(/\s{2,}/g, " ").trim();
        return {
            text: label ? (cleaned ? label + " " + cleaned : label) : cleaned,
            rank: rank,
        };
    }

    function resolutionLabelForRank(rank) {
        for (var i = 0; i < RESOLUTION_LABELS.length; i++) {
            if (RESOLUTION_LABELS[i].rank === rank) {
                return RESOLUTION_LABELS[i].label;
            }
        }
        return "";
    }

    function stripEpisodeToken(title, seasonNumber, episodeNumber) {
        var cleaned = title;
        var season = parseInt(seasonNumber, 10);
        var episode = parseInt(episodeNumber, 10);
        if (!isNaN(season) && !isNaN(episode)) {
            cleaned = cleaned.replace(new RegExp("[Ss]0*" + season + "[\\s._-]*[Ee]0*" + episode + "(?![0-9])", "i"), " ");
            cleaned = cleaned.replace(new RegExp("(^|[^0-9])0*" + season + "[xX]0*" + episode + "(?![0-9])", "i"), "$1 ");
            cleaned = cleaned.replace(new RegExp("\\bseason[\\s._-]*0*" + season + "\\b", "i"), " ");
            cleaned = cleaned.replace(new RegExp("\\bepisode[\\s._-]*0*" + episode + "\\b", "i"), " ");
        } else if (!isNaN(season)) {
            cleaned = cleaned.replace(new RegExp("[Ss]0*" + season + "(?![\\s._-]*[Ee]\\d)", "i"), " ");
            cleaned = cleaned.replace(new RegExp("\\bseason[\\s._-]*0*" + season + "\\b", "i"), " ");
        }
        return cleaned;
    }

    Vue.component("search-results-screen", {
        mixins: [rbmixin],
        data: function () {
            return {
                results: null,
                searchterm: "",
                query: "",
                richContentEnabled: localStorage.getItem("richContentEnabled") === "true",
                groups: [],
                other: [],
                openEpisodes: {},
                openSeasons: {},
                openResolutions: {},
                seasonDetails: {},
                seasonDetailsLoading: {},
                libraryTitles: [],
                pinnedTitle: null,
            };
        },
        methods: {
            back: function () {
                window.history.back();
            },
            goHome: function () {
                navigate("/");
            },
            onSearchSubmit: function () {
                var term = (this.query || "").trim();
                if (!term) {
                    return;
                }
                if (term.startsWith("magnet:")) {
                    navigate("/magnet/" + encodeURIComponent(encodeURIComponent(term)));
                    return;
                }
                saveSearchTerm(term);
                navigate("/search/" + term);
            },
            onResultClick: function (result, seasonNumber, episodeNumber) {
                rememberEpisodeTarget(seasonNumber, episodeNumber);
                if (result.filename) {
                    navigate("/magnet/" + encodeURIComponent(encodeURIComponent(result.magnet)) + "/" + encodeURIComponent(result.filename));
                } else if (result.magnet) {
                    navigate("/magnet/" + encodeURIComponent(encodeURIComponent(result.magnet)));
                } else if (result.torrent_link) {
                    navigate("/torrent/" + encodeURIComponent(result.torrent_link));
                }
            },
            onClearHistory: function () {
                clearHistory();
                this.results = [];
            },
            formatRating: function (value) {
                var number = Number(value);
                if (!isFinite(number)) {
                    return "";
                }
                return number.toFixed(1);
            },
            episodeCode: function (season, episode) {
                function pad(value) {
                    var number = parseInt(value, 10);
                    return (number < 10 ? "0" : "") + number;
                }
                return "S" + pad(season) + "E" + pad(episode);
            },
            formatAirDate: function (value) {
                var match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value || "");
                if (!match) {
                    return value || "";
                }
                var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
                var month = months[parseInt(match[2], 10) - 1];
                if (!month) {
                    return value;
                }
                return parseInt(match[3], 10) + " " + month + " " + match[1];
            },
            latestEpisodeResults: function (group) {
                var latest = group.latest_episode;
                if (!latest || !group.seasons) {
                    return [];
                }
                var season = null;
                for (var i = 0; i < group.seasons.length; i++) {
                    if (group.seasons[i].season === latest.season_number) {
                        season = group.seasons[i];
                        break;
                    }
                }
                if (!season) {
                    return [];
                }
                var buckets = this.episodeGroups(season);
                for (var j = 0; j < buckets.length; j++) {
                    if (buckets[j].episode === latest.episode_number) {
                        return buckets[j].results;
                    }
                }
                return [];
            },
            formatRuntime: function (minutes) {
                var total = parseInt(minutes, 10);
                if (!total || total < 1) {
                    return "";
                }
                var hours = Math.floor(total / 60);
                var mins = total % 60;
                if (!hours) {
                    return mins + " min";
                }
                if (!mins) {
                    return hours + "h";
                }
                return hours + "h " + mins + "m";
            },
            movieResultLabel: function (group, result) {
                var cleaned = stripKnownMovieTitle(result.title || "", group && group.title, group && group.year);
                var labelled = labelWithResolution(cleaned);
                return labelled.text || result.title;
            },
            sortByResolutionAndSeeds: function (results, describe) {
                return (results || []).slice().sort(function (a, b) {
                    var left = describe(a);
                    var right = describe(b);
                    if (left.rank !== right.rank) {
                        return right.rank - left.rank;
                    }
                    return (b.seeds || 0) - (a.seeds || 0);
                }).map(function (result) {
                    var info = describe(result);
                    return {
                        result: result,
                        label: info.text || result.title,
                        rank: info.rank,
                    };
                });
            },
            buildResolutionRows: function (labelledResults, isRankOpen, alwaysCollapse) {
                var collapse = alwaysCollapse || labelledResults.length > 10;
                var buckets = [];
                var indexByRank = {};
                labelledResults.forEach(function (item) {
                    var rank = item.rank;
                    if (indexByRank[rank] === undefined) {
                        indexByRank[rank] = buckets.length;
                        buckets.push({
                            rank: rank,
                            name: resolutionLabelForRank(rank) || "Other",
                            results: [],
                        });
                    }
                    buckets[indexByRank[rank]].results.push(item);
                });
                var rows = [];
                buckets.forEach(function (bucket) {
                    var hidden = collapse && bucket.results.length > 4 && !isRankOpen(bucket.rank);
                    var visible = hidden ? bucket.results.slice(0, 3) : bucket.results;
                    visible.forEach(function (item, index) {
                        rows.push({
                            type: "result",
                            key: (item.result.magnet || item.result.torrent_link || item.result.title) + ":" + bucket.rank + ":" + index,
                            result: item.result,
                            label: item.label,
                        });
                    });
                    if (hidden) {
                        var extra = bucket.results.length - 3;
                        rows.push({
                            type: "more",
                            key: "more:" + bucket.rank,
                            rank: bucket.rank,
                            label: bucket.name + " - " + extra + " more results...",
                        });
                    }
                });
                return rows;
            },
            resolutionOpenKey: function (group, rank) {
                return [group.tmdb_id || group.title, group.year || "", rank].join(":");
            },
            isResolutionOpen: function (group, rank) {
                return !!this.openResolutions[this.resolutionOpenKey(group, rank)];
            },
            showResolution: function (group, rank) {
                this.$set(this.openResolutions, this.resolutionOpenKey(group, rank), true);
            },
            movieResultRows: function (group) {
                var self = this;
                var labelled = this.sortByResolutionAndSeeds(group.results || [], function (result) {
                    var cleaned = stripKnownMovieTitle(result.title || "", group && group.title, group && group.year);
                    var info = labelWithResolution(cleaned);
                    return { text: info.text || result.title, rank: info.rank };
                });
                return this.buildResolutionRows(labelled, function (rank) {
                    return self.isResolutionOpen(group, rank);
                });
            },
            episodeResolutionOpenKey: function (group, season, episode, rank) {
                return ["episode", group.tmdb_id || group.title, season && season.season, episode && (episode.key || episode.episode), rank].join(":");
            },
            episodeResultRows: function (group, season, episode, results) {
                var self = this;
                var list = results || (episode && episode.results) || [];
                var labelled = this.sortByResolutionAndSeeds(list, function (result) {
                    return self.episodeVariation(group, season, episode, result);
                });
                return this.buildResolutionRows(labelled, function (rank) {
                    return !!self.openResolutions[self.episodeResolutionOpenKey(group, season, episode, rank)];
                }, true);
            },
            latestEpisodeRows: function (group) {
                var latest = group.latest_episode;
                if (!latest) {
                    return [];
                }
                return this.episodeResultRows(
                    group,
                    { season: latest.season_number },
                    { episode: latest.episode_number, key: String(latest.episode_number) },
                    this.latestEpisodeResults(group)
                );
            },
            onEpisodeRowClick: function (group, season, episode, row) {
                if (row.type === "more") {
                    this.$set(this.openResolutions, this.episodeResolutionOpenKey(group, season, episode, row.rank), true);
                    return;
                }
                var seasonNumber = season && season.season;
                var episodeNumber = episode && episode.episode;
                if (group.latest_episode && seasonNumber === undefined) {
                    seasonNumber = group.latest_episode.season_number;
                    episodeNumber = group.latest_episode.episode_number;
                }
                this.onResultClick(row.result, seasonNumber, episodeNumber);
            },
            onMovieRowClick: function (group, row) {
                if (row.type === "more") {
                    this.showResolution(group, row.rank);
                    return;
                }
                this.onResultClick(row.result);
            },
            libraryMatch: function (group) {
                var id = group && group.tmdb_id;
                if (!id) {
                    return null;
                }
                var titles = this.libraryTitles || [];
                for (var i = 0; i < titles.length; i++) {
                    if (titles[i].tmdb_id === id && titles[i].media_type === group.media_type) {
                        return titles[i];
                    }
                }
                return null;
            },
            isMovieWatched: function (group) {
                var match = this.libraryMatch(group);
                return !!(match && match.watched_at);
            },
            isEpisodeNumberWatched: function (group, seasonNumber, episodeNumber) {
                var match = this.libraryMatch(group);
                if (!match || episodeNumber === null || episodeNumber === undefined) {
                    return false;
                }
                var season = Number(seasonNumber);
                var episode = Number(episodeNumber);
                return (match.watched_episodes || []).some(function (item) {
                    return Number(item.season) === season && Number(item.episode) === episode;
                });
            },
            isEpisodeWatched: function (group, season, episode) {
                if (!episode || episode.episode === null || episode.episode === undefined) {
                    return false;
                }
                return this.isEpisodeNumberWatched(group, season && season.season, episode.episode);
            },
            loadLibrary: function () {
                var self = this;
                get("/api/library/", function (data) {
                    self.libraryTitles = data && data.titles ? data.titles : [];
                });
            },
            episodeGroups: function (season) {
                var groups = [];
                var indexByEpisode = {};
                var seasonRange = /\bseasons?\s+\d{1,2}\s*(?:to|thru|through|[-–—~])\s*(?:season\s+)?\d{1,2}\b/i;
                var codeRange = /(?:^|[^A-Za-z0-9])S\d{1,2}(?:[ ._-]*E\d{1,2})?\s*(?:to|thru|through|[-–—~])\s*S\d{1,2}/i;
                (season.episodes || []).forEach(function (result, index) {
                    var title = result.title || "";
                    var seasonEpisode = title.match(/[Ss]\d{1,2}[ ._-]*[Ee](\d{1,2})/);
                    var cross = title.match(/(?:^|[^0-9])\d{1,2}x(\d{1,2})(?:[^0-9]|$)/);
                    var coversSeveralSeasons = seasonRange.test(title) || codeRange.test(title);
                    var episodeNumber = coversSeveralSeasons ? null : seasonEpisode ? parseInt(seasonEpisode[1], 10) : cross ? parseInt(cross[1], 10) : null;
                    var key = episodeNumber === null ? "season-pack" : String(episodeNumber);
                    if (indexByEpisode[key] === undefined) {
                        indexByEpisode[key] = groups.length;
                        groups.push({
                            episode: episodeNumber,
                            key: key,
                            label: episodeNumber === null ? "Full season" : "Episode " + episodeNumber,
                            results: [],
                        });
                    }
                    groups[indexByEpisode[key]].results.push(result);
                });
                return groups;
            },
            seasonOpenKey: function (group, season) {
                return [group.tmdb_id || group.title, season.season].join(":");
            },
            isSeasonOpen: function (group, season) {
                if (!group.seasons || group.seasons.length <= 1) {
                    return true;
                }
                return !!this.openSeasons[this.seasonOpenKey(group, season)];
            },
            toggleSeason: function (group, season) {
                if (!group.seasons || group.seasons.length <= 1) {
                    return;
                }
                var key = this.seasonOpenKey(group, season);
                var opening = !this.openSeasons[key];
                this.$set(this.openSeasons, key, opening);
                if (opening) {
                    this.ensureSeasonDetails(group, season);
                }
            },
            prefetchOpenSeasons: function () {
                var self = this;
                (this.groups || []).forEach(function (group) {
                    (group.seasons || []).forEach(function (season) {
                        if (self.isSeasonOpen(group, season)) {
                            self.ensureSeasonDetails(group, season);
                        }
                    });
                });
            },
            ensureSeasonDetails: function (group, season) {
                if (!group || !group.tmdb_id || group.media_type !== "tv") {
                    return;
                }
                var key = this.seasonOpenKey(group, season);
                if (this.seasonDetails[key] || this.seasonDetailsLoading[key]) {
                    return;
                }
                this.$set(this.seasonDetailsLoading, key, true);
                var self = this;
                var generation = this.seasonRequestGeneration || 0;
                function finish(episodes) {
                    if (generation !== (self.seasonRequestGeneration || 0)) {
                        return;
                    }
                    self.$set(self.seasonDetails, key, episodes);
                    self.$set(self.seasonDetailsLoading, key, false);
                }
                var request = get(
                    "/api/tv/" + encodeURIComponent(group.tmdb_id) + "/season/" + encodeURIComponent(season.season) + "/",
                    function (data) {
                        finish((data && data.episodes) || []);
                    }
                );
                if (request && request.fail) {
                    request.fail(function () {
                        finish([]);
                    });
                }
            },
            isSeasonLoading: function (group, season) {
                if (!group || !group.tmdb_id) {
                    return false;
                }
                return this.seasonDetails[this.seasonOpenKey(group, season)] === undefined;
            },
            episodeHasAired: function (info) {
                var match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(info && info.air_date || "");
                if (!match) {
                    return false;
                }
                var aired = new Date(parseInt(match[1], 10), parseInt(match[2], 10) - 1, parseInt(match[3], 10));
                var today = new Date();
                today.setHours(0, 0, 0, 0);
                return aired.getTime() <= today.getTime();
            },
            seasonEpisodes: function (group, season) {
                var details = this.seasonDetails[this.seasonOpenKey(group, season)];
                var tmdbEpisodes = Array.isArray(details) ? details : [];
                var buckets = this.episodeGroups(season);
                var packs = [];
                var byEpisode = {};
                buckets.forEach(function (bucket) {
                    if (bucket.episode === null) {
                        packs = packs.concat(bucket.results);
                        return;
                    }
                    byEpisode[bucket.episode] = bucket.results;
                });
                var tmdbByNumber = {};
                tmdbEpisodes.forEach(function (episode) {
                    tmdbByNumber[episode.episode_number] = episode;
                });
                var numbers = [];
                var seen = {};
                function addNumber(value) {
                    var number = parseInt(value, 10);
                    if (isNaN(number) || seen[number]) {
                        return;
                    }
                    seen[number] = true;
                    numbers.push(number);
                }
                var self = this;
                function isUnreleased(number) {
                    var info = tmdbByNumber[number];
                    return !!(info && info.air_date && !self.episodeHasAired(info));
                }
                if (packs.length && tmdbEpisodes.length) {
                    tmdbEpisodes.forEach(function (episode) {
                        if (!self.episodeHasAired(episode)) {
                            return;
                        }
                        addNumber(episode.episode_number);
                    });
                }
                Object.keys(byEpisode).forEach(function (value) {
                    var number = parseInt(value, 10);
                    if (isUnreleased(number)) {
                        return;
                    }
                    addNumber(number);
                });
                if (!numbers.length && packs.length) {
                    return [{
                        episode: null,
                        key: "season-pack",
                        label: "Full season",
                        details: null,
                        results: packs,
                    }];
                }
                numbers.sort(function (a, b) {
                    return a - b;
                });
                return numbers.map(function (number) {
                    var own = byEpisode[number] || [];
                    var results = own.slice();
                    packs.forEach(function (result) {
                        results.push(Object.assign({ seasonPack: true }, result));
                    });
                    var info = tmdbByNumber[number] || null;
                    return {
                        episode: number,
                        key: String(number),
                        label: (info && info.name) || ("Episode " + number),
                        details: info,
                        results: results,
                    };
                });
            },
            episodeOpenKey: function (group, season, episode) {
                return [group.tmdb_id || group.title, season.season, episode.key].join(":");
            },
            isEpisodeOpen: function (group, season, episode) {
                return !!this.openEpisodes[this.episodeOpenKey(group, season, episode)];
            },
            toggleEpisode: function (group, season, episode) {
                var key = this.episodeOpenKey(group, season, episode);
                this.$set(this.openEpisodes, key, !this.openEpisodes[key]);
            },
            latestOpenKey: function (group) {
                var latest = group.latest_episode;
                return [group.tmdb_id || group.title, latest.season_number, String(latest.episode_number)].join(":");
            },
            isLatestOpen: function (group) {
                return !!this.openEpisodes[this.latestOpenKey(group)];
            },
            toggleLatest: function (group) {
                var key = this.latestOpenKey(group);
                this.$set(this.openEpisodes, key, !this.openEpisodes[key]);
            },
            episodeVariation: function (group, season, episode, result) {
                var title = result.title || "";
                var cleaned = title;
                var showPattern = flexibleShowPattern(group && group.title);
                if (showPattern) {
                    cleaned = cleaned.replace(new RegExp("(^|[^A-Za-z0-9])" + showPattern + "(?![A-Za-z0-9])", "i"), "$1 ");
                }
                if (group && group.year) {
                    cleaned = cleaned.replace(new RegExp("\\(\\s*" + group.year + "\\s*\\)", "g"), " ");
                    cleaned = cleaned.replace(new RegExp("(^|[^0-9])" + group.year + "(?![0-9])", "g"), "$1 ");
                }
                cleaned = stripEpisodeToken(cleaned, season && season.season, episode && episode.episode);
                if (!episode || episode.episode === null || result.seasonPack) {
                    cleaned = cleaned.replace(/\bseasons?\s+\d{1,2}\s*(?:to|thru|through|[-–—~])\s*(?:season\s+)?\d{1,2}\b/ig, " ");
                    cleaned = cleaned.replace(/(?:^|[^A-Za-z0-9])S\d{1,2}(?:[ ._-]*E\d{1,2})?\s*(?:to|thru|through|[-–—~])\s*S\d{1,2}(?:[ ._-]*E\d{1,2})?/ig, " ");
                    cleaned = cleaned.replace(/(?:^|[^A-Za-z0-9])[Ss]\d{1,2}(?![A-Za-z0-9])/g, " ");
                    cleaned = cleaned.replace(/\bseason\s+\d{1,2}\b/ig, " ");
                    cleaned = cleaned.replace(/\bcomplete\b/ig, " ");
                    cleaned = cleaned.replace(/\b(?:mp4|mkv|avi|m4v)\b/ig, " ");
                }
                cleaned = cleaned.replace(/[\[\]()]/g, " ");
                cleaned = cleaned.replace(/^[\s._:-]+/, "").replace(/[\s._:-]+$/, "").replace(/\s{2,}/g, " ").trim();
                var labelled = labelWithResolution(cleaned);
                return {
                    text: labelled.text || title,
                    rank: labelled.rank,
                };
            },
            episodeVariationLabel: function (group, season, episode, result) {
                return this.episodeVariation(group, season, episode, result).text;
            },
            loadRichSearch: function () {
                var self = this;
                var generation = this.richSearchGeneration;
                this.results = null;
                this.groups = [];
                this.other = [];
                this.openEpisodes = {};
                this.openSeasons = {};
                this.openResolutions = {};
                this.seasonDetails = {};
                this.seasonDetailsLoading = {};
                this.seasonRequestGeneration = (this.seasonRequestGeneration || 0) + 1;
                var endpoint = "/api/rich_search/" + encodeURIComponent(this.searchterm);
                if (this.pinnedTitle) {
                    endpoint += "?media=" + encodeURIComponent(this.pinnedTitle.media) + "&tmdb=" + encodeURIComponent(this.pinnedTitle.tmdb);
                }
                this.richRequest = get(endpoint, function (data) {
                    if (generation !== self.richSearchGeneration) {
                        return;
                    }
                    self.richRequest = null;
                    self.groups = Array.isArray(data.groups) ? data.groups : [];
                    self.other = Array.isArray(data.other) ? data.other : [];
                    self.prefetchOpenSeasons();
                    if (self.groups.length === 0 && self.other.length === 0) {
                        if (self.pinnedTitle) {
                            self.results = [];
                            return;
                        }
                        self.richContentEnabled = false;
                        self.startFlatSearch();
                        return;
                    }
                    self.results = [];
                    self.focusFirstResult();
                });
                this.richRequest.fail(function (request, status) {
                    if (status === "abort" || generation !== self.richSearchGeneration) {
                        return;
                    }
                    self.richRequest = null;
                    if (self.pinnedTitle) {
                        self.groups = [];
                        self.other = [];
                        self.results = [];
                        return;
                    }
                    self.richContentEnabled = false;
                    self.startFlatSearch();
                });
            },
            focusFirstResult: function () {
                rbsetTimeout(function () {
                    var firstTr = document.getElementsByTagName("tr")[0];
                    if (firstTr) {
                        firstTr.focus();
                    }
                });
            },
            startFlatSearch: function () {
                var self = this;
                this.results = null;
                this.groups = [];
                this.other = [];
                var fallbackSearch = function () {
                    self.flatRequest = get("/api/search/" + encodeURIComponent(self.searchterm), function (data) {
                        self.flatRequest = null;
                        self.results = data.results;
                        self.focusFirstResult();
                    });
                };
                // Stream results over SSE: render a re-ranked snapshot as
                // each indexer responds instead of waiting for the slowest.
                var focused = false;
                this.eventsource = subscribe(
                    "/api/search_events/" + self.searchterm,
                    function (data) {
                        if (data.results) {
                            self.results = data.results;
                            if (!focused && data.results.length) {
                                focused = true;
                                self.focusFirstResult();
                            }
                        }
                        if (data.done) {
                            // Settle an empty stream so the spinner stops.
                            if (self.results === null) {
                                self.results = data.results || [];
                                self.focusFirstResult();
                            }
                            self.eventsource = null;
                        }
                    },
                    function () {
                        self.eventsource = null;
                        if (self.results === null) {
                            fallbackSearch();
                        }
                    }
                );
            },
        },
        template: "#search-results-screen-template",
        created: function () {
            var self = this;
            this.searchterm = this.params ? this.params.searchterm : "";
            this.query = this.searchterm === "[history]" || this.searchterm === "[favorites]" ? "" : this.searchterm;
            this.pinnedTitle = pinnedTitleFromLocation();
            this.richSearchGeneration = 0;

            function fetchAndApplyStatus(results) {
                var hashes = [];
                var torrent_links = [];
                results.forEach(function (r) {
                    if (r.magnet) {
                        hashes.push(get_hash(r.magnet));
                    } else if (r.torrent_link) {
                        torrent_links.push(r.torrent_link);
                    }
                });
                if (hashes.length === 0 && torrent_links.length === 0) return;
                $.ajax({
                    url: "/api/magnet_status/",
                    type: "POST",
                    contentType: "application/json",
                    data: JSON.stringify({ hashes: hashes, torrent_links: torrent_links }),
                    success: function (data) {
                        results.forEach(function (r) {
                            if (r.magnet) {
                                var hash = get_hash(r.magnet);
                                r.status = data.statuses[hash] || null;
                            } else if (r.torrent_link) {
                                r.status = data.statuses[r.torrent_link] || null;
                            }
                        });
                        self.results = results.slice(); // trigger Vue reactivity
                    }
                });
            }

            if (this.searchterm === "[history]") {
                this.results = getHistory();
                fetchAndApplyStatus(this.results);
                this.focusFirstResult();
            } else if (this.searchterm === "[favorites]") {
                this.results = getFavorites();
                fetchAndApplyStatus(this.results);
                this.focusFirstResult();
            } else if ((this.richContentEnabled || this.pinnedTitle) && this.searchterm) {
                this.loadRichSearch();
            } else {
                this.startFlatSearch();
            }
            syncLibraryFromLocalHistory();
            this.loadLibrary();
            this.keylistener = keylistener.bind({});
            document.addEventListener("keydown", this.keylistener);
        },
        destroyed: function () {
            document.removeEventListener("keydown", this.keylistener);
            this.richSearchGeneration += 1;
            if (this.richRequest) {
                this.richRequest.abort();
                this.richRequest = null;
            }
            if (this.flatRequest) {
                this.flatRequest.abort();
                this.flatRequest = null;
            }
            if (this.eventsource) {
                this.eventsource.close();
                this.eventsource = null;
            }
        },
    });

    Vue.component("torrent-link-screen", {
        mixins: [rbmixin],
        template: "#torrent-link-screen-template",
        created: function () {
            post(
                "/api/torrent_url_to_magnet/",
                {
                    url: this.params.torrent_link,
                },
                function (data) {
                    navigate(
                        "/magnet/" +
                            encodeURIComponent(
                                encodeURIComponent(data.magnet_link)
                            ),
                        true
                    );
                }
            );
        },
    });

    Vue.component("filelist-screen", {
        mixins: [rbmixin],
        data: function () {
            return { results: null, isTorrentFavorited: false, completedFiles: [], fileStatuses: {}, openedSingle: false };
        },
        template: "#filelist-screen-template",
        methods: {
            back: function () {
                window.history.back();
            },
            isCompleted: function (filename) {
                return this.completedFiles.indexOf(filename) !== -1;
            },
            getFileStatus: function (filename) {
                return this.fileStatuses[filename] || null;
            },
            checkFavorited: function () {
                var magnetHash = get_hash(this.params.magnet_link);
                var favorites = getFavorites();
                this.isTorrentFavorited = favorites.some(function (f) {
                    return get_hash(f.magnet) === magnetHash && !f.filename;
                });
            },
            toggleFavorite: function () {
                var magnet = this.params.magnet_link;
                if (this.isTorrentFavorited) {
                    removeFavorite(magnet, "");
                } else {
                    saveFavorite(magnet, "");
                }
                this.isTorrentFavorited = !this.isTorrentFavorited;
            },
        },
        created: function () {
            this.checkFavorited();
            this.completedFiles = getCompletedFiles(this.params.magnet_link);
            this.keylistener = keylistener.bind({});
            document.addEventListener("keydown", this.keylistener);
            post("/api/magnet_files/", {
                magnet_link: this.params.magnet_link,
            });
            var self = this;
            var magnet_hash = get_hash(this.params.magnet_link);
            function openChosenFile(filename) {
                if (self.openedSingle) {
                    return;
                }
                self.openedSingle = true;
                sessionStorage.removeItem("rapidbayEpisodeTarget");
                if (self.eventsource) {
                    self.eventsource.close();
                    self.eventsource = null;
                }
                navigate(
                    "/magnet/" + encodeURIComponent(encodeURIComponent(self.params.magnet_link)) + "/" + encodeURIComponent(filename),
                    true
                );
            }
            function applyFiles(data) {
                var files = data && data.files;
                if (files && files.length === 1 && !isExecutableFilename(files[0])) {
                    openChosenFile(files[0]);
                    return;
                }
                var target = readEpisodeTarget();
                if (target && files && files.length) {
                    var chosen = pickEpisodeFile(files, target.season, target.episode);
                    if (chosen) {
                        openChosenFile(chosen);
                        return;
                    }
                    sessionStorage.removeItem("rapidbayEpisodeTarget");
                }
                self.results = files;
                self.fileStatuses = data.file_statuses || {};
                rbsetTimeout(function () {
                    // Find first unwatched file
                    var firstUnwatched = 0;
                    for (var i = 0; i < self.results.length; i++) {
                        if (self.completedFiles.indexOf(self.results[i]) === -1) {
                            firstUnwatched = i;
                            break;
                        }
                    }
                    var rows = document.getElementsByTagName("tr");
                    if (rows[firstUnwatched]) {
                        rows[firstUnwatched].focus();
                    }
                });
            }
            function pollFiles() {
                (function get_files() {
                    get("/api/magnet/" + magnet_hash + "/", function (data) {
                        if (data.files == null) {
                            rbsetTimeout(get_files, 1000);
                            return;
                        }
                        applyFiles(data);
                    });
                })();
            }
            // Server pushes the file list the moment metadata resolves
            this.eventsource = subscribe(
                "/api/magnet_events/" + magnet_hash + "/",
                function (data) {
                    if (data.files) {
                        applyFiles(data);
                    }
                    if (data.done) {
                        self.eventsource = null;
                    }
                },
                function () {
                    self.eventsource = null;
                    pollFiles();
                }
            );
        },
        destroyed: function () {
            document.removeEventListener("keydown", this.keylistener);
            if (this.eventsource) {
                this.eventsource.close();
                this.eventsource = null;
            }
        },
    });

    Vue.component("download-screen", {
        mixins: [rbmixin],
        template: "#download-screen-template",
        data: function () {
            return {
                progress: null,
                status: null,
                peers: null,
                heading: "",
                subheading: null,
                play_link: null,
                subtitles: [],
                supported: null,
                downloadProgress: null,
                canStream: false,
                streamRequested: false,
                hlsFailed: false,
                streamMessage: null
            };
        },
        methods: {
            preventchange: function (e) {
                e.preventDefault();
                e.target.value = window.location.origin + this.play_link;
            },
            back: function () {
                window.history.back();
            },
            startStream: function () {
                var self = this;
                var magnet_hash = get_hash(this.params.magnet_link);
                self.streamRequested = true;
                self.streamMessage = null;
                post("/api/magnet/" + magnet_hash + "/" + encodeURIComponent(this.params.filename) + "/stream", {}, function (data) {
                    if (data && data.started) return;
                    // Backend declined — re-show ▶ and surface the reason so
                    // the user knows whether to retry, give up, or wait.
                    self.streamRequested = false;
                    var reasons = {
                        disabled: "Streaming is disabled.",
                        unsupported_format: "This file format can't be streamed live.",
                        codec_failed: "Streaming failed for this file's codec.",
                        capacity: "Server is at streaming capacity. Try again shortly.",
                        not_ready: "Not enough data buffered yet — wait a moment.",
                        no_torrent: "Torrent isn't ready yet.",
                        file_not_found: "File not found in torrent.",
                        invalid_path: "Invalid filename.",
                    };
                    self.streamMessage = (data && reasons[data.reason]) || "Couldn't start the stream.";
                });
            },
            onStreamError: function () {
                // HLS playback failed (e.g. unsupported codec) — drop back to loading screen
                this.play_link = null;
                this.streamRequested = false;
                this.canStream = false;
                this.hlsFailed = true;
            },
        },
        created: function () {
            this.keylistener = keylistener.bind({});
            document.addEventListener("keydown", this.keylistener);
            post("/api/magnet_download/", {
                magnet_link: this.params.magnet_link,
                filename: this.params.filename,
            });
            saveToHistory(this.params.magnet_link);
            reportLibraryEvents([{
                event: "download",
                magnet: this.params.magnet_link,
                title: get_magnet_name(this.params.magnet_link),
                filename: this.params.filename || "",
                ts: Date.now(),
            }]);
            var self = this;
            var magnet_hash = get_hash(this.params.magnet_link);
            function applyFileInfo(data) {
                self.status = data.status;
                self.progress = data.progress;
                var text = data.status.replace(/_/g, " ");
                self.heading =
                    data.progress === 0 || data.progress
                        ? text +
                          " (" +
                          Math.round(data.progress * 100) +
                          "%)"
                        : text;
                var subheadingParts = [];
                if (data.source === "http") {
                    subheadingParts.push("HTTP");
                } else if (data.peers === 0 || data.peers) {
                    subheadingParts.push(data.peers + " Peers");
                }
                if (data.download_rate) {
                    var mbps = (data.download_rate / 1000000).toFixed(2);
                    subheadingParts.push(mbps + " MB/s");
                }
                self.subheading = subheadingParts.length
                    ? subheadingParts.join(" · ")
                    : null;
                // Set play link: prefer MP4 (ready state), fall back to HLS for early playback.
                // For HLS, we tag the URL with the current subtitle count so that
                // when new VTTs arrive the regenerated master playlist gets refetched
                // by hls.js (cache-bust). The player's `:key` ignores the query
                // string so subs-count changes only swap the source internally
                // (preserving playback position) instead of remounting the video.
                if (data.status === "ready" && data.filename) {
                    var mp4Link = "/play/" + magnet_hash + "/" + encodeURIComponent(data.filename);
                    if (self.play_link !== mp4Link) {
                        self.play_link = mp4Link;
                    }
                    self.supported = !!data.supported;
                } else if (data.hls_filename && !self.hlsFailed) {
                    var hlsSubCount = (data.hls_subtitles || []).length;
                    var hlsLink = "/play/" + magnet_hash + "/" + encodeURIComponent(data.hls_filename) + "?subs=" + hlsSubCount;
                    var alreadyHls = self.play_link && self.play_link.indexOf(".m3u8") !== -1;
                    if (!self.play_link || alreadyHls) {
                        if (self.play_link !== hlsLink) {
                            self.play_link = hlsLink;
                        }
                        self.supported = true;
                    }
                }
                // Track download progress for display in player header
                self.downloadProgress = data.status !== "ready" ? (data.progress || null) : null;
                // Pass <track>-style subtitles only for MP4 playback. For HLS, subtitles
                // are declared in the master playlist via EXT-X-MEDIA so hls.js (and
                // native HLS clients) manage them — adding <track> elements alongside
                // confuses the native track selection.
                var playingHls = self.play_link && self.play_link.indexOf(".m3u8") !== -1;
                if (!window.isSafari && !playingHls) {
                    var subs = data.subtitles || [];
                    self.subtitles = subs.map(function (sub) {
                        return {
                            language: sub
                                .substring(sub.lastIndexOf("_") + 1)
                                .replace(".vtt", ""),
                            url: "/play/" + magnet_hash + "/" + sub,
                        };
                    });
                } else if (playingHls) {
                    self.subtitles = [];
                }
                // Show stream button when backend confirms enough data is available
                self.canStream = !!data.can_stream;
                // can_stream means no stream is running (no playlist, no active
                // ffmpeg, not marked failed) — so a previously requested stream
                // was reaped (stall or viewer timeout). Re-arm the button so
                // the user can request it again without reloading.
                if (self.canStream && self.streamRequested) {
                    self.streamRequested = false;
                }
                // Stream accepted but ffmpeg hasn't produced a playlist yet —
                // say so instead of showing a bare progress screen.
                if (data.hls_pending) {
                    self.streamMessage = "Starting stream\u2026";
                } else if (self.streamMessage === "Starting stream\u2026") {
                    self.streamMessage = null;
                }
            }
            function pollFileInfo() {
                (function get_file_info() {
                    get(
                        "/api/magnet/" +
                            magnet_hash +
                            "/" +
                            encodeURIComponent(self.params.filename),
                        function (data) {
                            applyFileInfo(data);
                            if (self.status !== "ready") {
                                rbsetTimeout(get_file_info, 1000);
                            }
                        }
                    );
                })();
            }
            // Server pushes status changes (progress, peers, ready) as they happen
            this.eventsource = subscribe(
                "/api/magnet_events/" +
                    magnet_hash +
                    "/" +
                    encodeURIComponent(self.params.filename),
                function (data) {
                    applyFileInfo(data);
                    if (data.done) {
                        self.eventsource = null;
                    }
                },
                function () {
                    self.eventsource = null;
                    if (self.status !== "ready") {
                        pollFileInfo();
                    }
                }
            );
        },
        destroyed: function () {
            document.removeEventListener("keydown", this.keylistener);
            if (this.eventsource) {
                this.eventsource.close();
                this.eventsource = null;
            }
        },
    });

    var vm = new Vue({
        el: "#app",
        data: { screen: null, params: {} },
    });

    function display_view(view_name) {
        return function (params) {
            clear_pending_requests();
            clear_pending_callbacks();

            if (params && params.magnet_link) {
                params.magnet_link = decodeURIComponent(params.magnet_link);
                params.magnet_link = decodeURIComponent(params.magnet_link);
            }
            vm.screen = view_name;
            vm.params = params;
        };
    }

    var router = new Navigo(window.location.origin);
    router
        .on({
            "search/": display_view("search-results-screen"),
            "search/:searchterm": display_view("search-results-screen"),
            "torrent/:torrent_link/": display_view("torrent-link-screen"),
            "magnet/:magnet_link/": display_view("filelist-screen"),
            "magnet/:magnet_link/:filename": display_view("download-screen"),
            "*": display_view("search-screen"),
        })
        .resolve();
})();
