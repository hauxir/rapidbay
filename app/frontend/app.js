(function () {
    window.isSafari = navigator.vendor && navigator.vendor.indexOf("Apple") > -1;
    window.isChrome = /Chrome/i.test(navigator.userAgent);
    if (navigator.serviceWorker) {
        navigator.serviceWorker.register("/sw.js");
    }
    var navigated = false;

    if (!window.location.origin) {
        window.location.origin =
            window.location.protocol +
            "//" +
            window.location.hostname +
            (window.location.port ? ":" + window.location.port : "");
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

    function get_hash(magnet_link) {
        var hash_start = magnet_link.indexOf("btih:") + 5;
        var hash_end = magnet_link.indexOf("&");
        if (hash_end == -1) return magnet_link.substr(hash_start).toLowerCase();
        return magnet_link.substr(hash_start, hash_end - hash_start).toLowerCase();
    }

    function navigate(path, replaceState) {
        if (replaceState) {
            router.historyAPIUpdateMethod("replaceState");
        } else {
            router.historyAPIUpdateMethod("pushState");
        }
        navigated = true;
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
            progress_el && (progress_el.style.width = this.progress * 100 + "%");
        },
    });

    Vue.component("player", {
        props: ["url", "subtitles", "back"],
        data: function () {
            return {
                isDesktop: !/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini|Mobile|mobile|CriOS/i.test(
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

            function getNextFile() {
                return new Promise(function (resolve) {
                    get("/api/next_file/" + magnet_hash + "/" + filename, function (data) {
                        resolve(data.next_filename)
                    });
                });
            }

            var video = document.getElementsByTagName("video")[0];

            try {
                new Plyr(video, {
                    settings: ["captions"],
                    fullscreen: {
                        container: "body",
                    },
                    captions: {update: true},
                });
            } catch (e) {
                console.error(e);
                video.setAttribute("controls", true);
            }

            video.onplay = function () {
                getNextFile().then(function (next_file) {
                    if (next_file) {
                        $.post("/api/magnet_download/", {
                            magnet_link: decodeURIComponent(
                                decodeURIComponent(location.pathname.split("/")[2])
                            ),
                            filename: next_file,
                        });
                    }
                });
            };

            video.onended = function () {
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
                            navigate(next_path);
                        });
                    }
                });
            };
            video.play();
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
        },
        template: "#player-template",
    });

    Vue.component("chromecast-button", {
        template: "#chromecast-button-template",
        methods: {
            cast: function () {
                var root = window.location.origin;
                var video = document.getElementsByTagName("video")[0];
                var current_subtitle = null;
                if (video.plyr) {
                    current_subtitle = video.plyr.captions.currentTrackNode;
                } else {
                    var subtitle_tracks = Array.from(video.textTracks);
                    current_subtitle = subtitle_tracks.find(function (t) {
                        return t.mode !== "disabled";
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

    Vue.component("search-screen", {
        template: "#search-screen-template",
        data: function () {
            return {searchterm: ""};
        },
        methods: {
            onSubmit: function (e) {
                e.preventDefault();
                if (this.searchterm.startsWith("magnet:")) {
                    navigate(
                        "/magnet/" + encodeURIComponent(encodeURIComponent(this.searchterm))
                    );
                } else {
                    navigate("/search/" + this.searchterm);
                }
            },
        },
        created: function () {
            if (router.lastRouteResolved().url.toLowerCase() === "/registerhandler") {
                navigator.registerProtocolHandler(
                    "magnet",
                    router.root + "/magnet/%s",
                    "RapidBay"
                );
            }
        },
    });

    Vue.component("search-results-screen", {
        mixins: [rbmixin],
        data: function () {
            return {results: null, searchterm: ""};
        },
        methods: {
            back: function () {
                if (navigated) {
                    window.history.back();
                } else {
                    navigate("/", true);
                }
            },
        },
        template: "#search-results-screen-template",
        created: function () {
            this.searchterm = this.params ? this.params.searchterm : "";
            var self = this;
            get("/api/search/" + self.searchterm, function (data) {
                self.results = data.results;
            });
        },
    });

    Vue.component("torrent-link-screen", {
        mixins: [rbmixin],
        template: "#torrent-link-screen-template",
        created: function () {
            $.post(
                "/api/torrent_url_to_magnet/",
                {
                    url: this.params.torrent_link,
                },
                function (data) {
                    navigate(
                        "/magnet/" +
                        encodeURIComponent(encodeURIComponent(data.magnet_link)),
                        true
                    );
                }
            );
        },
    });

    Vue.component("filelist-screen", {
        mixins: [rbmixin],
        data: function () {
            return {results: null};
        },
        template: "#filelist-screen-template",
        methods: {
            back: function () {
                if (navigated) {
                    window.history.back();
                } else {
                    router.historyAPIUpdateMethod("pushState");
                    navigate("/");
                }
            },
        },
        created: function () {
            router.historyAPIUpdateMethod("pushState");
            $.post("/api/magnet_files/", {magnet_link: this.params.magnet_link});
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
                    }
                );
            })();
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
            };
        },
        methods: {
            preventchange: function (e) {
                e.preventDefault();
                e.target.value = window.location.origin + this.play_link;
            },
            back: function () {
                if (navigated) {
                    window.history.back();
                } else {
                    navigate(
                        window.location.pathname.substring(
                            0,
                            window.location.pathname.lastIndexOf("/")
                        ),
                        true
                    );
                }
            },
        },
        created: function () {
            $.post("/api/magnet_download/", {
                magnet_link: this.params.magnet_link,
                filename: this.params.filename,
            });
            var self = this;
            var magnet_hash = get_hash(this.params.magnet_link);
            (function get_file_info() {
                get(
                    "/api/magnet/" + magnet_hash + "/" + self.params.filename,
                    function (data) {
                        self.status = data.status;
                        self.progress = data.progress;
                        var text = data.status.replace(/_/g, " ");
                        self.heading =
                            data.progress === 0 || data.progress
                                ? text + " (" + Math.round(data.progress * 100) + "%)"
                                : text;
                        self.subheading =
                            data.peers === 0 || data.peers ? data.peers + " Peers" : null;
                        self.play_link = data.filename
                            ? "/play/" + magnet_hash + "/" + data.filename
                            : null;
                        if (!window.isSafari) {
                            self.subtitles = data.subtitles
                                ? data.subtitles.map(function (sub) {
                                    return {
                                        language: sub
                                            .substring(sub.lastIndexOf("_") + 1)
                                            .replace(".vtt", ""),
                                        url: "/play/" + magnet_hash + "/" + sub,
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
    });

    var vm = new Vue({
        el: "#app",
        data: {screen: null, params: {}},
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
