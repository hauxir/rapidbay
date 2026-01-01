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
        if (history.length > 5) {
            history = history.slice(0, 5);
        }
        localStorage.setItem("searchHistory", JSON.stringify(history));
    }

    function getSearchHistory() {
        return JSON.parse(localStorage.getItem("searchHistory") || "[]");
    }

    function markFileCompleted(magnet, filename) {
        var hash = get_hash(magnet);
        var completed = JSON.parse(localStorage.getItem("completedFiles") || "{}");
        if (!completed[hash]) completed[hash] = [];
        if (completed[hash].indexOf(filename) === -1) {
            completed[hash].push(filename);
        }
        localStorage.setItem("completedFiles", JSON.stringify(completed));
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

    function saveVideoPosition(magnet, filename, position) {
        localStorage.setItem(getVideoPositionKey(magnet, filename), position.toString());
    }

    function getVideoPosition(magnet, filename) {
        return parseFloat(localStorage.getItem(getVideoPositionKey(magnet, filename))) || 0;
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

    Vue.component("player", {
        props: ["supported", "url", "subtitles", "back", "magnet", "filename"],
        data: function () {
            return {
                isDesktop:
                    !/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini|Mobile|mobile|CriOS/i.test(
                        navigator.userAgent
                    ),
                isChrome: window.isChrome,
                hovering: false,
            };
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
                            resolve(data.next_filename);
                        }
                    );
                });
            }

            var video = document.getElementsByTagName("video")[0];

            video.addEventListener("play", function () {
                getNextFile().then(function (next_file) {
                    if (next_file) {
                        post("/api/magnet_download/", {
                            magnet_link: decodeURIComponent(
                                decodeURIComponent(
                                    location.pathname.split("/")[2]
                                )
                            ),
                            filename: next_file,
                        });
                    }
                });
            });

            video.addEventListener("ended", function () {
                getNextFile().then(function (next_file) {
                    if (next_file) {
                        var next_path =
                            window.location.pathname.substring(
                                0,
                                window.location.pathname.lastIndexOf("/")
                            ) +
                            "/" +
                            next_file;
                        navigate("/", true);
                        rbsetTimeout(function () {
                            navigate(next_path, true);
                        });
                    }
                });
            });
            video.play();

            // Restore saved position
            var savedPosition = getVideoPosition(self.magnet, self.filename);
            if (savedPosition > 0) {
                video.currentTime = savedPosition;
            }

            // Save position periodically
            self.positionInterval = setInterval(function () {
                if (!video.paused && video.currentTime > 0) {
                    saveVideoPosition(self.magnet, self.filename, video.currentTime);
                }
            }, 5000);

            // Save position on pause
            video.addEventListener("pause", function () {
                saveVideoPosition(self.magnet, self.filename, video.currentTime);
            });

            // Clear position and mark completed when video ends
            video.addEventListener("ended", function () {
                clearVideoPosition(self.magnet, self.filename);
                markFileCompleted(self.magnet, self.filename);
            });

            var captionLanguage = localStorage.getItem("captionLanguage");
            var tracks = video.textTracks;
            for (var i = 0; i < tracks.length; i++) {
                var track = tracks[i];
                track.mode = "disabled";
            }
            if (captionLanguage) {
                var currentTrack;
                for (var i = 0; i < tracks.length; i++) {
                    var track = tracks[i];
                    track.mode = "hidden";
                    if (!currentTrack && track.language === captionLanguage) {
                        currentTrack = track;
                    }
                }
                if (currentTrack) {
                    currentTrack.mode = "showing";
                }
            }
            this.captionChangeListener = function (e) {
                console.log(e);
                var tracks = e.currentTarget;
                var captionLanguage;
                for (var i = 0; i < tracks.length; i++) {
                    var track = tracks[i];
                    if (track.mode === "showing") {
                        captionLanguage = track.language;
                    }
                }
                if (captionLanguage) {
                    window.localStorage.setItem(
                        "captionLanguage",
                        captionLanguage
                    );
                } else {
                    window.localStorage.removeItem("captionLanguage");
                }
            };

            video.textTracks.addEventListener(
                "change",
                this.captionChangeListener
            );

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
                } else {
                    self.mousemove_listener();
                }
            };

            document.addEventListener("keydown", this.videokeylistener, true);
        },

        created: function () {
            var timeout;
            var duration = 2800;
            var self = this;
            this.mousemove_listener = function () {
                self.hovering = true;
                clearTimeout(timeout);
                timeout = rbsetTimeout(function () {
                    self.hovering = false;
                }, duration);
            };
            this.mousemove_listener();
            document.addEventListener("mousemove", this.mousemove_listener);
            document.addEventListener("touchstart", this.mousemove_listener);
            document.addEventListener("click", this.mousemove_listener);
        },
        destroyed: function () {
            document.removeEventListener("mousemove", this.mousemove_listener);
            document.removeEventListener("touchstart", this.mousemove_listener);
            document.removeEventListener("click", this.mousemove_listener);
            document.removeEventListener(
                "keydown",
                this.videokeylistener,
                true
            );
            document.removeEventListener("keydown", this.keylistener);
            if (this.positionInterval) {
                clearInterval(this.positionInterval);
            }
            var video = document.getElementsByTagName("video")[0];
            if (video) {
                video.textTracks.removeEventListener(
                    "change",
                    this.captionChangeListener
                );
                if (video.currentTime > 0) {
                    saveVideoPosition(this.magnet, this.filename, video.currentTime);
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
            return { currentCaption: null, tracks: [] };
        },
        methods: {
            flipCaptions: function () {
                var video = document.getElementsByTagName("video")[0];
                var currentIndex = null;
                var tracks = video.textTracks;
                for (var i = 0; i < tracks.length; i++) {
                    var track = tracks[i];
                    if (track.mode === "showing") {
                        currentIndex = i;
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
                }
            },
        },
        mounted: function () {
            var video = document.getElementsByTagName("video")[0];
            var self = this;
            if (video) {
                this.tracks = video.textTracks;
                for (var i = 0; i < this.tracks.length; i++) {
                    var track = this.tracks[i];
                    if (track.mode === "showing") {
                        this.currentCaption = track.language;
                    }
                }
                this.captionChangeListener = function (e) {
                    self.tracks = video.textTracks;
                    self.currentCaption = null;
                    for (var i = 0; i < self.tracks.length; i++) {
                        var track = self.tracks[i];
                        if (track.mode === "showing") {
                            self.currentCaption = track.language;
                        }
                    }
                };
                video.textTracks.addEventListener(
                    "change",
                    this.captionChangeListener
                );
            }
        },
        destroyed: function () {
            var video = document.getElementsByTagName("video")[0];
            if (video) {
                video.textTracks.removeEventListener(
                    "change",
                    this.captionChangeListener
                );
            }
        },
    });

    Vue.component("chromecast-button", {
        template: "#chromecast-button-template",
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
                var media = {
                    content: video.src,
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

    Vue.component("search-screen", {
        template: "#search-screen-template",
        data: function () {
            return { searchterm: "", searchHistory: [] };
        },
        methods: {
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
            goHistory: function () {
                navigate("/search/[history]");
            },
            goTrending: function () {
                navigate("/search/");
            },
            goFavorites: function () {
                navigate("/search/[favorites]");
            },
        },
        mounted: function () {
            this.searchHistory = getSearchHistory();

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
                var isTopbarButton = document.activeElement && document.activeElement.closest(".topbar-home");
                var isHistoryItem = document.activeElement && document.activeElement.closest(".search-history");
                var isInput = document.activeElement && document.activeElement.tagName === "INPUT";
                if (lowername === "enter" && (isTopbarButton || isHistoryItem)) {
                    e.preventDefault();
                    document.activeElement.click();
                } else if (lowername === "arrowdown") {
                    e.preventDefault();
                    if (isInput) {
                        var firstItem = document.querySelector(".search-history-item");
                        if (firstItem) {
                            firstItem.focus();
                        }
                    } else if (isHistoryItem) {
                        focusNextElement();
                    } else {
                        $("input").focus().click();
                    }
                } else if (lowername === "arrowup") {
                    e.preventDefault();
                    if (isHistoryItem) {
                        var items = document.querySelectorAll(".search-history-item");
                        var idx = Array.prototype.indexOf.call(items, document.activeElement);
                        if (idx === 0) {
                            $("input").focus().click();
                        } else {
                            focusPrevElement();
                        }
                    } else if (!isTopbarButton) {
                        $(".topbar-home button:first").focus();
                    }
                } else if (lowername === "arrowright" && !isInput) {
                    e.preventDefault();
                    focusNextElement();
                } else if (lowername === "arrowleft" && !isInput) {
                    e.preventDefault();
                    focusPrevElement();
                }
            };

            document.addEventListener("keydown", this.keylistener);
        },
        destroyed: function () {
            document.removeEventListener("keydown", this.keylistener);
        },
    });

    Vue.component("search-results-screen", {
        mixins: [rbmixin],
        data: function () {
            return { results: null, searchterm: "" };
        },
        methods: {
            back: function () {
                window.history.back();
            },
            onResultClick: function (result) {
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
        },
        template: "#search-results-screen-template",
        created: function () {
            var self = this;
            this.searchterm = this.params ? this.params.searchterm : "";

            if (this.searchterm === "[history]") {
                this.results = getHistory();
                rbsetTimeout(function () {
                    var firstTr = document.getElementsByTagName("tr")[0];
                    if (firstTr) {
                        firstTr.focus();
                    }
                });
            } else if (this.searchterm === "[favorites]") {
                this.results = getFavorites();
                rbsetTimeout(function () {
                    var firstTr = document.getElementsByTagName("tr")[0];
                    if (firstTr) {
                        firstTr.focus();
                    }
                });
            } else {
                get("/api/search/" + self.searchterm, function (data) {
                    self.results = data.results;
                    rbsetTimeout(function () {
                        var firstTr = document.getElementsByTagName("tr")[0];
                        if (firstTr) {
                            firstTr.focus();
                        }
                    });
                });
            }
            this.keylistener = keylistener.bind({});
            document.addEventListener("keydown", this.keylistener);
        },
        destroyed: function () {
            document.removeEventListener("keydown", this.keylistener);
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
            return { results: null, isTorrentFavorited: false, completedFiles: [] };
        },
        template: "#filelist-screen-template",
        methods: {
            back: function () {
                window.history.back();
            },
            isCompleted: function (filename) {
                return this.completedFiles.indexOf(filename) !== -1;
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
            (function get_files() {
                get(
                    "/api/magnet/" + get_hash(self.params.magnet_link) + "/",
                    function (data) {
                        if (data.files == null) {
                            rbsetTimeout(get_files, 1000);
                            return;
                        }
                        self.results = data.files;
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
                );
            })();
        },
        destroyed: function () {
            document.removeEventListener("keydown", this.keylistener);
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
		supported: null
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
        },
        created: function () {
            this.keylistener = keylistener.bind({});
            document.addEventListener("keydown", this.keylistener);
            post("/api/magnet_download/", {
                magnet_link: this.params.magnet_link,
                filename: this.params.filename,
            });
            saveToHistory(this.params.magnet_link);
            var self = this;
            var magnet_hash = get_hash(this.params.magnet_link);
            (function get_file_info() {
                get(
                    "/api/magnet/" +
                        magnet_hash +
                        "/" +
                        encodeURIComponent(self.params.filename),
                    function (data) {
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
                        self.subheading =
                            data.peers === 0 || data.peers
                                ? data.peers + " Peers"
                                : null;
                        self.play_link = data.filename
                            ? "/play/" +
                              magnet_hash +
                              "/" +
                              encodeURIComponent(data.filename)
                            : null;
			self.supported = !!data.supported
                        if (!window.isSafari) {
                            self.subtitles = data.subtitles
                                ? data.subtitles.map(function (sub) {
                                      return {
                                          language: sub
                                              .substring(
                                                  sub.lastIndexOf("_") + 1
                                              )
                                              .replace(".vtt", ""),
                                          url:
                                              "/play/" +
                                              magnet_hash +
                                              "/" +
                                              sub,
                                      };
                                  })
                                : [];
                        }
                        if (self.status !== "ready") {
                            rbsetTimeout(get_file_info, 1000);
                        }
                    }
                );
            })();
        },
        destroyed: function () {
            document.removeEventListener("keydown", this.keylistener);
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
