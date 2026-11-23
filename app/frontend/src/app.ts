(function () {
    // Response shapes mirror the pydantic models in app/app.py.
    interface FileStatus {
        status: string;
        filename?: string | null;
        subtitles?: string[] | null;
        supported?: boolean | null;
        progress?: number | null;
        peers?: number | null;
        source?: string | null;
        download_rate?: number | null;
        hls_filename?: string | null;
        hls_subtitles?: string[] | null;
        hls_pending?: boolean | null;
        can_stream?: boolean | null;
    }

    interface FilesResponse {
        files: string[] | null;
        file_statuses?: { [filename: string]: string } | null;
    }

    interface NextFileResponse {
        next_filename?: string | null;
        next_magnet?: string | null;
    }

    interface MagnetStatusResponse {
        statuses: { [hashOrLink: string]: string | null };
    }

    interface StreamResponse {
        started?: boolean;
        reason?: string;
    }

    // Server-sent events carry the same payloads plus a final {done: true}.
    type StreamEvent<T> = T & { done?: boolean };

    // A row on the search results screen: a search hit, a history entry or a
    // favorite.
    interface ResultRow {
        title: string;
        magnet?: string | null;
        torrent_link?: string | null;
        filename?: string;
        seeds?: number;
        status?: string | null;
    }

    interface HistoryEntry {
        magnet: string;
        title: string;
        ts: number;
    }

    interface Favorite {
        magnet: string;
        filename: string;
        title: string;
        ts: number;
    }

    interface Subtitle {
        language: string;
        url: string;
    }

    var keylistener = function (e: KeyboardEvent) {
        var name = e.key;
        var lowername = name.toLowerCase();
        if (lowername === "enter") {
            e.preventDefault();
            clickActiveElement();
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

    function clickActiveElement() {
        var active = document.activeElement;
        if (active instanceof HTMLElement) {
            active.click();
        }
    }

    function blurActiveElement() {
        var active = document.activeElement;
        if (active instanceof HTMLElement) {
            active.blur();
        }
    }

    function focusNextElement() {
        var selectables = $(':focusable:not([tabindex="-1"])');
        var currentIndex = selectables.index($(":focus"));
        blurActiveElement();
        selectables.eq(currentIndex + 1).trigger("focus");
    }

    function focusPrevElement() {
        var selectables = $(':focusable:not([tabindex="-1"])');
        var currentIndex = selectables.index($(":focus"));
        blurActiveElement();
        selectables.eq(currentIndex - 1).trigger("focus");
    }

    document.addEventListener("mousemove", function () {
        if (document.activeElement && document.activeElement.tagName !== "INPUT") {
            blurActiveElement();
        }
    });

    window.isSafari =
        // eslint-disable-next-line @typescript-eslint/no-deprecated -- no standard replacement for Safari detection
        !!navigator.vendor && navigator.vendor.indexOf("Apple") > -1;

    window.isChrome = /Chrome/i.test(navigator.userAgent);
    if ("serviceWorker" in navigator) {
        void navigator.serviceWorker.register("/sw.js");
    }

    if (!window.location.origin) {
        (window.location as { origin: string }).origin =
            window.location.protocol +
            "//" +
            window.location.hostname +
            (window.location.port ? ":" + window.location.port : "");
    }

    if (!(String.prototype as Partial<Pick<string, "startsWith">>).startsWith) {
        String.prototype.startsWith = function (search: string, pos?: number) {
            return this.slice(pos || 0, search.length) === search;
        };
    }

    var pending_callbacks: number[] = [];
    var pending_requests: JQuery.jqXHR<unknown>[] = [];

    function rbsetTimeout(f: () => void, s?: number) {
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
            if (r) r.abort();
        }
    }

    function restore_cookie() {
        if (!document.cookie) {
            var saved = localStorage.getItem("cookie");
            if (saved) {
                document.cookie = saved;
            }
        }
    }

    // T is the shape of the server's JSON (see the interfaces above); it is
    // not checked at runtime.
    // eslint-disable-next-line @typescript-eslint/no-unnecessary-type-parameters
    function get<T>(url: string, callback: (data: T) => void) {
        var request: JQuery.jqXHR<unknown>;
        restore_cookie();
        function _callback(data: T) {
            pending_requests = pending_requests.filter(function (req) {
                return req !== request;
            });
            callback(data);
        }
        request = $.get(url, _callback);
        pending_requests.push(request);
        return request;
    }

    // eslint-disable-next-line @typescript-eslint/no-unnecessary-type-parameters
    function post<T>(url: string, data: object, callback?: (data: T) => void) {
        restore_cookie();
        $.post(url, data, callback || null);
    }

    // Subscribe to a server-sent-events endpoint. Calls callback per event,
    // closes on {done: true}, and invokes fallback (e.g. to start polling)
    // if SSE is unavailable or the stream errors.
    function subscribe<T>(
        url: string,
        callback: (data: StreamEvent<T>) => void,
        fallback: () => void
    ): EventSource | null {
        if (!("EventSource" in window)) {
            fallback();
            return null;
        }
        restore_cookie();
        var es = new EventSource(url);
        es.onmessage = function (e: MessageEvent<unknown>) {
            if (typeof e.data !== "string") return;
            var parsed: unknown = JSON.parse(e.data);
            // type-coverage:ignore-next-line -- server JSON, see get()
            var data = parsed as StreamEvent<T>;
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

    // Reads JSON this app stored under key; its shape is not checked.
    function readStored<T>(key: string, fallback: T): T {
        var raw = localStorage.getItem(key);
        if (!raw) return fallback;
        var parsed: unknown = JSON.parse(raw);
        // type-coverage:ignore-next-line -- written by this app
        return parsed as T;
    }

    function saveToHistory(magnet: string) {
        var history = getHistory();
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

    function getHistory(): HistoryEntry[] {
        return readStored<HistoryEntry[]>("downloadHistory", []);
    }

    function clearHistory() {
        localStorage.removeItem("downloadHistory");
        localStorage.removeItem("completedFiles");
        localStorage.removeItem("searchHistory");
    }

    function saveSearchTerm(term: string) {
        if (!term || term.trim() === "") return;
        var history = getSearchHistory();
        history = history.filter(function (t) {
            return t.toLowerCase() !== term.toLowerCase();
        });
        history.unshift(term);
        if (history.length > 4) {
            history = history.slice(0, 4);
        }
        localStorage.setItem("searchHistory", JSON.stringify(history));
    }

    function getSearchHistory(): string[] {
        return readStored<string[]>("searchHistory", []);
    }

    function getAllCompletedFiles(): { [hash: string]: string[] } {
        return readStored<{ [hash: string]: string[] }>("completedFiles", {});
    }

    function markFileCompleted(magnet: string, filename: string) {
        var hash = get_hash(magnet);
        var completed = getAllCompletedFiles();
        var files = completed[hash] || (completed[hash] = []);
        if (files.indexOf(filename) === -1) {
            files.push(filename);
        }
        localStorage.setItem("completedFiles", JSON.stringify(completed));
    }

    function getCompletedFiles(magnet: string): string[] {
        var hash = get_hash(magnet);
        return getAllCompletedFiles()[hash] || [];
    }

    function getStoredFavorites(): Favorite[] {
        return readStored<Favorite[]>("favorites", []);
    }

    function getFavorites(): Favorite[] {
        return getStoredFavorites().sort(function (a, b) {
            return (a.title || "").localeCompare(b.title || "");
        });
    }

    function saveFavorite(magnet: string, filename: string) {
        var magnetHash = get_hash(magnet);
        var favorites = getStoredFavorites().filter(function (f) {
            return get_hash(f.magnet) !== magnetHash || f.filename !== filename;
        });
        var title = filename || get_magnet_name(magnet);
        favorites.unshift({ magnet: magnet, filename: filename, title: title, ts: Date.now() });
        if (favorites.length > 100) {
            favorites = favorites.slice(0, 100);
        }
        localStorage.setItem("favorites", JSON.stringify(favorites));
    }

    function removeFavorite(magnet: string, filename: string) {
        var magnetHash = get_hash(magnet);
        var favorites = getStoredFavorites().filter(function (f) {
            return get_hash(f.magnet) !== magnetHash || f.filename !== filename;
        });
        localStorage.setItem("favorites", JSON.stringify(favorites));
    }

    function getVideoPositionKey(magnet: string, filename: string) {
        return "videoPosition_" + get_hash(magnet) + "_" + filename;
    }

    function saveVideoPosition(magnet: string, filename: string, position: number) {
        localStorage.setItem(getVideoPositionKey(magnet, filename), position.toString());
    }

    function getVideoPosition(magnet: string, filename: string) {
        return parseFloat(localStorage.getItem(getVideoPositionKey(magnet, filename)) || "") || 0;
    }

    function clearVideoPosition(magnet: string, filename: string) {
        localStorage.removeItem(getVideoPositionKey(magnet, filename));
    }

    function get_hash(magnet_link: string) {
        var hash_start = magnet_link.indexOf("btih:") + 5;
        var hash_end = magnet_link.indexOf("&");
        if (hash_end == -1) return magnet_link.substring(hash_start).toLowerCase();
        return magnet_link
            .substring(hash_start, hash_end)
            .toLowerCase();
    }

    function get_magnet_name(magnet_link: string) {
        var match = magnet_link.match(/dn=([^&]+)/);
        if (match && match[1]) {
            return decodeURIComponent(match[1].replace(/\+/g, " "));
        }
        return get_hash(magnet_link);
    }

    // The player's <video>, absent outside the player screen.
    function getVideo(): HTMLVideoElement | undefined {
        return document.getElementsByTagName("video")[0];
    }

    function pathSegment(path: string, index: number) {
        return path.split("/")[index] || "";
    }

    function navigate(path: string, replaceState?: boolean) {
        if (replaceState) {
            router.historyAPIUpdateMethod("replaceState");
        } else {
            router.historyAPIUpdateMethod("pushState");
        }
        router.navigate(path);
    }

    // Registers a component whose `this` is Vue plus Self: the component's
    // props, data, computed values and methods, and the non-reactive fields
    // (listeners, hls.js instance, event source) it keeps on itself. Prop
    // names and data() must match Self.
    type ComponentDefinition<Self> = Omit<ComponentOptions<Vue & Self>, "props" | "data"> & {
        props?: (keyof Self & string)[];
        data?: (this: Vue & Self) => Partial<Self>;
    } & ThisType<Vue & Self>;

    function component<Self>(name: string, options: ComponentDefinition<Self>) {
        // Vue 2.5's typings give every method `this: Vue`; at runtime `this` is
        // the full instance that Self describes.
        // type-coverage:ignore-next-line
        Vue.component(name, options as unknown as ComponentOptions<Vue>);
    }

    // Route params per screen; Navigo fills the names in the route patterns
    // registered at the bottom of this file.
    interface SearchParams {
        searchterm?: string;
    }
    interface TorrentParams {
        torrent_link: string;
    }
    interface MagnetParams {
        magnet_link: string;
    }
    interface FileParams extends MagnetParams {
        filename: string;
    }

    interface ScreenProps<Params> {
        params: Params;
        navigate: typeof navigate;
    }

    var rbmixin: ComponentOptions<Vue> = {
        props: ["params"],
        methods: {
            navigate: navigate,
        },
    };

    interface LoadingSpinner {
        heading: string;
        subheading: string | null;
        progress: number | null;
    }

    component<LoadingSpinner>("loading-spinner", {
        props: ["heading", "subheading", "progress"],
        template: "#loading-spinner-template",
        updated: function () {
            var progress_el = this.$refs["progress"];
            if (progress_el instanceof HTMLElement) {
                progress_el.style.width = String((this.progress || 0) * 100) + "%";
            }
        },
    });

    interface Player {
        supported: boolean | null;
        url: string;
        subtitles: Subtitle[];
        back: () => void;
        magnet: string;
        filename: string;
        downloadProgress: number | null;
        downloadStatus: string | null;
        onStreamError: (() => void) | undefined;
        isDesktop: boolean;
        isChrome: boolean;
        hovering: boolean;
        hls?: Hls | null;
        positionInterval?: number;
        addTrackListener: () => void;
        captionChangeListener: () => void;
        videokeylistener: (event: KeyboardEvent) => void;
        mousemove_listener: () => void;
    }

    component<Player>("player", {
        props: ["supported", "url", "subtitles", "back", "magnet", "filename", "downloadProgress", "downloadStatus", "onStreamError"],
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
        computed: {
            downloadStatusLabel: function (): string {
                if (!this.downloadStatus) return "";
                var text = this.downloadStatus.replace(/_/g, " ");
                return text.charAt(0).toUpperCase() + text.slice(1);
            },
        },
        watch: {
            // url changes within the same playback session when subs become
            // available (cache-buster increments). Reload hls.js's source in
            // place — the parent's :key strips the query string so we don't
            // remount the <video> here. Playback time and play/pause state
            // are preserved across the reload.
            url: function (newUrl: string, oldUrl: string) {
                if (!newUrl || newUrl === oldUrl) return;
                if (newUrl.split("?")[0] !== oldUrl.split("?")[0]) return;
                const video = getVideo();
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
        mounted: function () {
            var magnet_hash = pathSegment(this.url, 2);
            var filename = (function (l) {
                return decodeURIComponent(l[l.length - 1] || "");
            })(location.pathname.split("/"));
            var self = this;

            function getNextFile() {
                return new Promise<NextFileResponse>(function (resolve) {
                    get<NextFileResponse>(
                        "/api/next_file/" + magnet_hash + "/" + filename,
                        function (data) {
                            resolve(data);
                        }
                    );
                });
            }

            const video = getVideo();
            if (!video) return;
            var videoUrl = window.location.origin + self.url;
            var isHLS = self.url.indexOf(".m3u8") !== -1;
            var savedPosition = getVideoPosition(self.magnet, self.filename);

            if (isHLS && typeof Hls !== "undefined" && Hls.isSupported()) {
                var errorRecoveries = 0;
                var maxRecoveries = 5;
                var hls = new Hls({
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
                self.hls = hls;
                hls.on(Hls.Events.ERROR, function (_event, data) {
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
                hls.loadSource(videoUrl);
                hls.attachMedia(video);
            } else if (isHLS && video.canPlayType("application/vnd.apple.mpegurl")) {
                video.src = videoUrl;
            } else {
                video.src = videoUrl;
            }

            video.addEventListener("play", function () {
                void getNextFile().then(function (data) {
                    if (data.next_filename) {
                        var magnet = data.next_magnet || decodeURIComponent(
                            decodeURIComponent(pathSegment(location.pathname, 2))
                        );
                        post("/api/magnet_download/", {
                            magnet_link: magnet,
                            filename: data.next_filename,
                        });
                    }
                });
            });

            video.addEventListener("ended", function () {
                void getNextFile().then(function (data) {
                    if (data.next_filename) {
                        var magnet = data.next_magnet || decodeURIComponent(
                            decodeURIComponent(pathSegment(location.pathname, 2))
                        );
                        var next_path = "/magnet/" + encodeURIComponent(encodeURIComponent(magnet)) + "/" + encodeURIComponent(data.next_filename);
                        navigate("/", true);
                        rbsetTimeout(function () {
                            navigate(next_path, true);
                        });
                    }
                });
            });
            void video.play();

            // Restore saved position (the hls.js path resumes via the
            // startPosition config above instead).
            if (savedPosition > 0 && !self.hls) {
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

            function normalizeLanguage(lang: string | null) {
                return lang ? (lang.split("-")[0] || "").toLowerCase() : lang;
            }
            var applyCaptionPreference = function () {
                var tracks = video.textTracks;
                var captionLanguage = normalizeLanguage(localStorage.getItem("captionLanguage"));
                if (!captionLanguage) return;
                // Don't mutate modes unless we're actually selecting one — hls.js's
                // text-track poll treats any non-"disabled" track as the active
                // subtitle, so blanket-hiding tracks would auto-select whichever
                // happens to be last in the list.
                var hasShowing = false;
                var currentTrack: TextTrack | undefined;
                for (var i = 0; i < tracks.length; i++) {
                    var candidate = tracks[i];
                    if (!candidate) continue;
                    if (candidate.mode === "showing") {
                        hasShowing = true;
                    }
                    if (!currentTrack && normalizeLanguage(candidate.language) === captionLanguage) {
                        currentTrack = candidate;
                    }
                }
                if (hasShowing || !currentTrack) return;
                currentTrack.mode = "showing";
            };
            var tracks = video.textTracks;
            for (var i = 0; i < tracks.length; i++) {
                var track = tracks[i];
                if (track) track.mode = "disabled";
            }
            applyCaptionPreference();
            this.addTrackListener = function () {
                applyCaptionPreference();
            };
            video.textTracks.addEventListener("addtrack", this.addTrackListener);
            this.captionChangeListener = function () {
                var tracks = video.textTracks;
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
                    var track = tracks[i];
                    if (track && track.mode === "showing") {
                        lastShowingIndex = i;
                    }
                }
                var captionLanguage: string | null = null;
                for (var j = 0; j < tracks.length; j++) {
                    var showing = tracks[j];
                    if (!showing || showing.mode !== "showing") continue;
                    if (j !== lastShowingIndex) {
                        // Setting mode re-fires "change", but the next pass
                        // sees only one showing and exits without further
                        // mutation — no infinite loop.
                        showing.mode = "hidden";
                    } else {
                        captionLanguage = showing.language;
                    }
                }
                if (captionLanguage) {
                    window.localStorage.setItem(
                        "captionLanguage",
                        normalizeLanguage(captionLanguage) || ""
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
                const active = document.activeElement;
                const videoSelected =
                    !!active &&
                    ["video", "body"].indexOf(active.tagName.toLowerCase()) !== -1;
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
                        void video.play();
                    }
                } else if (
                    event.key.toLowerCase() === "mediarewind" &&
                    videoSelected
                ) {
                    location.href = video.src;
                }
            };

            document.addEventListener("keydown", this.videokeylistener, true);
        },

        created: function () {
            var timeout: number | undefined;
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
            if (this.positionInterval) {
                clearInterval(this.positionInterval);
            }
            if (this.hls) {
                this.hls.destroy();
                this.hls = null;
            }
            var video = getVideo();
            if (video) {
                video.textTracks.removeEventListener(
                    "change",
                    this.captionChangeListener
                );
                video.textTracks.removeEventListener(
                    "addtrack",
                    this.addTrackListener
                );
                if (video.currentTime > 0) {
                    saveVideoPosition(this.magnet, this.filename, video.currentTime);
                }
            }
        },
        template: "#player-template",
    });

    component<object>("fullscreen-button", {
        template: "#fullscreen-button-template",
        methods: {
            toggleFullscreen: function () {
                var root = document.documentElement;
                if (
                    !document.fullscreenElement && // alternative standard method
                    !document.mozFullScreenElement &&
                    !document.webkitFullscreenElement
                ) {
                    // current working methods
                    // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition -- missing in older browsers
                    if (root.requestFullscreen) {
                        void root.requestFullscreen();
                    } else if (root.mozRequestFullScreen) {
                        root.mozRequestFullScreen();
                    } else if (root.webkitRequestFullscreen) {
                        // Legacy WebKit flag, not in the DOM typings.
                        var flag = "ALLOW_KEYBOARD_INPUT" in Element ? Element.ALLOW_KEYBOARD_INPUT : undefined;
                        root.webkitRequestFullscreen(typeof flag === "number" ? flag : undefined);
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

    interface CaptionButton {
        currentCaption: string | null;
        trackCount: number;
        captionChangeListener: () => void;
        trackListMutationListener: () => void;
    }

    component<CaptionButton>("caption-button", {
        template: "#caption-button-template",
        data: function () {
            return { currentCaption: null, trackCount: 0 };
        },
        methods: {
            flipCaptions: function () {
                var video = getVideo();
                if (!video) return;
                var current: TextTrack | undefined;
                var next: TextTrack | undefined;
                var tracks = video.textTracks;
                // Ensure all tracks are at least "hidden" so they load content
                for (var i = 0; i < tracks.length; i++) {
                    var track = tracks[i];
                    if (!track) continue;
                    if (track.mode === "showing") {
                        current = track;
                        next = tracks[i + 1];
                    } else if (track.mode === "disabled") {
                        track.mode = "hidden";
                    }
                }
                var first = tracks[0];
                if (current) {
                    current.mode = "hidden";
                    if (next) {
                        next.mode = "showing";
                        this.currentCaption = next.language;
                    } else {
                        this.currentCaption = null;
                    }
                } else if (first) {
                    first.mode = "showing";
                    this.currentCaption = first.language;
                }
            },
        },
        mounted: function () {
            const video = getVideo();
            var self = this;
            if (!video) return;
            // TextTrackList is a live, non-plain object — Vue 2 can't observe
            // its length, and the `change` event only fires on mode changes,
            // not on track additions. With HLS, subtitle tracks are appended
            // by hls.js after mount, so we have to mirror the count into a
            // reactive data field and listen to `addtrack`/`removetrack`.
            function showingLanguage(tracks: TextTrackList) {
                var language: string | null = null;
                for (var i = 0; i < tracks.length; i++) {
                    var track = tracks[i];
                    if (track && track.mode === "showing") {
                        language = track.language;
                    }
                }
                return language;
            }
            self.trackCount = video.textTracks.length;
            var initial = showingLanguage(video.textTracks);
            if (initial !== null) {
                self.currentCaption = initial;
            }
            this.captionChangeListener = function () {
                self.currentCaption = showingLanguage(video.textTracks);
            };
            this.trackListMutationListener = function () {
                self.trackCount = video.textTracks.length;
            };
            video.textTracks.addEventListener("change", this.captionChangeListener);
            video.textTracks.addEventListener("addtrack", this.trackListMutationListener);
            video.textTracks.addEventListener("removetrack", this.trackListMutationListener);
        },
        destroyed: function () {
            var video = getVideo();
            if (!video) return;
            video.textTracks.removeEventListener("change", this.captionChangeListener);
            video.textTracks.removeEventListener("addtrack", this.trackListMutationListener);
            video.textTracks.removeEventListener("removetrack", this.trackListMutationListener);
        },
    });

    component<{ videoUrl: string | null }>("chromecast-button", {
        template: "#chromecast-button-template",
        props: ["videoUrl"],
        methods: {
            cast: function () {
                var root = window.location.origin;
                var video = getVideo();
                if (!video) return;
                var subtitle_tracks = Array.from(video.textTracks);
                var current_subtitle = subtitle_tracks.find(function (t) {
                    return t.mode !== "disabled" && t.mode !== "hidden";
                });
                var current_subtitle_url = current_subtitle
                    ? root + current_subtitle.id
                    : null;
                var contentUrl = this.videoUrl ? root + this.videoUrl : video.src;
                var media: ChromecastMedia = {
                    content: contentUrl,
                    title: "RapidBay",
                    // Continue on the TV where the browser was; a video that
                    // has finished starts over rather than loading at its end.
                    time: video.ended ? 0 : video.currentTime || 0,
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

    interface FavoriteButton {
        magnet: string;
        filename: string;
        isFavorited: boolean;
        checkFavorited: () => void;
    }

    component<FavoriteButton>("favorite-button", {
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

    interface SearchScreen {
        searchterm: string;
        searchHistory: string[];
        keylistener: (e: KeyboardEvent) => void;
    }

    component<SearchScreen>("search-screen", {
        template: "#search-screen-template",
        data: function () {
            return { searchterm: "", searchHistory: [] };
        },
        methods: {
            onSubmit: function (e: Event) {
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
            onHistoryClick: function (term: string) {
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
                    clickActiveElement();
                } else if (lowername === "arrowdown") {
                    e.preventDefault();
                    if (isInput) {
                        var firstItem = document.querySelector<HTMLElement>(".search-history-item");
                        if (firstItem) {
                            firstItem.focus();
                        }
                    } else if (isHistoryItem) {
                        focusNextElement();
                    } else {
                        $("input").trigger("focus").trigger("click");
                    }
                } else if (lowername === "arrowup") {
                    e.preventDefault();
                    if (isHistoryItem) {
                        var items = document.querySelectorAll(".search-history-item");
                        var idx = document.activeElement ? Array.from(items).indexOf(document.activeElement) : -1;
                        if (idx === 0) {
                            $("input").trigger("focus").trigger("click");
                        } else {
                            focusPrevElement();
                        }
                    } else if (!isTopbarButton) {
                        $(".topbar-home button:first").trigger("focus");
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

    interface SearchResultsScreen extends ScreenProps<SearchParams | null> {
        results: ResultRow[] | null;
        searchterm: string;
        eventsource: EventSource | null;
        keylistener: (e: KeyboardEvent) => void;
    }

    component<SearchResultsScreen>("search-results-screen", {
        mixins: [rbmixin],
        data: function () {
            return { results: null, searchterm: "" };
        },
        methods: {
            back: function () {
                window.history.back();
            },
            onResultClick: function (result: ResultRow) {
                if (result.filename) {
                    navigate("/magnet/" + encodeURIComponent(encodeURIComponent(result.magnet || "")) + "/" + encodeURIComponent(result.filename));
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
            this.searchterm = (this.params && this.params.searchterm) || "";

            function fetchAndApplyStatus(results: ResultRow[]) {
                var hashes: string[] = [];
                var torrent_links: string[] = [];
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
                    success: function (data: MagnetStatusResponse) {
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
                var history = getHistory();
                this.results = history;
                fetchAndApplyStatus(history);
                rbsetTimeout(function () {
                    var firstTr = document.getElementsByTagName("tr")[0];
                    if (firstTr) {
                        firstTr.focus();
                    }
                });
            } else if (this.searchterm === "[favorites]") {
                var favorites = getFavorites();
                this.results = favorites;
                fetchAndApplyStatus(favorites);
                rbsetTimeout(function () {
                    var firstTr = document.getElementsByTagName("tr")[0];
                    if (firstTr) {
                        firstTr.focus();
                    }
                });
            } else {
                var focusFirstResult = function () {
                    rbsetTimeout(function () {
                        var firstTr = document.getElementsByTagName("tr")[0];
                        if (firstTr) {
                            firstTr.focus();
                        }
                    });
                };
                var fallbackSearch = function () {
                    get<{ results: ResultRow[] }>("/api/search/" + self.searchterm, function (data) {
                        self.results = data.results;
                        focusFirstResult();
                    });
                };
                // Stream results over SSE: render a re-ranked snapshot as
                // each indexer responds instead of waiting for the slowest.
                var focused = false;
                this.eventsource = subscribe<{ results?: ResultRow[] }>(
                    "/api/search_events/" + self.searchterm,
                    function (data) {
                        if (data.results) {
                            self.results = data.results;
                            if (!focused && data.results.length) {
                                focused = true;
                                focusFirstResult();
                            }
                        }
                        if (data.done) {
                            // Stream ended without ever delivering a snapshot
                            // (no indexer returned anything): settle to an
                            // empty list so the spinner stops and the empty
                            // state renders instead of loading forever.
                            if (self.results === null) {
                                self.results = data.results || [];
                                focusFirstResult();
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
            }
            this.keylistener = keylistener.bind({});
            document.addEventListener("keydown", this.keylistener);
        },
        destroyed: function () {
            document.removeEventListener("keydown", this.keylistener);
            if (this.eventsource) {
                this.eventsource.close();
                this.eventsource = null;
            }
        },
    });

    component<ScreenProps<TorrentParams>>("torrent-link-screen", {
        mixins: [rbmixin],
        template: "#torrent-link-screen-template",
        created: function () {
            post<{ magnet_link: string }>(
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

    interface FilelistScreen extends ScreenProps<MagnetParams> {
        results: string[] | null;
        isTorrentFavorited: boolean;
        completedFiles: string[];
        fileStatuses: { [filename: string]: string };
        eventsource: EventSource | null;
        keylistener: (e: KeyboardEvent) => void;
        checkFavorited: () => void;
    }

    component<FilelistScreen>("filelist-screen", {
        mixins: [rbmixin],
        data: function () {
            return { results: null, isTorrentFavorited: false, completedFiles: [], fileStatuses: {} };
        },
        template: "#filelist-screen-template",
        methods: {
            back: function () {
                window.history.back();
            },
            isCompleted: function (filename: string) {
                return this.completedFiles.indexOf(filename) !== -1;
            },
            getFileStatus: function (filename: string) {
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
            function applyFiles(data: FilesResponse) {
                self.results = data.files;
                self.fileStatuses = data.file_statuses || {};
                rbsetTimeout(function () {
                    // Find first unwatched file
                    var results = self.results || [];
                    var firstUnwatched = 0;
                    for (var i = 0; i < results.length; i++) {
                        var result = results[i];
                        if (result !== undefined && self.completedFiles.indexOf(result) === -1) {
                            firstUnwatched = i;
                            break;
                        }
                    }
                    var row = document.getElementsByTagName("tr")[firstUnwatched];
                    if (row) {
                        row.focus();
                    }
                });
            }
            function pollFiles() {
                (function get_files() {
                    get<FilesResponse>("/api/magnet/" + magnet_hash + "/", function (data) {
                        if (data.files == null) {
                            rbsetTimeout(get_files, 1000);
                            return;
                        }
                        applyFiles(data);
                    });
                })();
            }
            // Server pushes the file list the moment metadata resolves
            this.eventsource = subscribe<FilesResponse>(
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

    interface DownloadScreen extends ScreenProps<FileParams> {
        progress: number | null;
        status: string | null;
        peers: number | null;
        heading: string;
        subheading: string | null;
        play_link: string | null;
        subtitles: Subtitle[];
        supported: boolean | null;
        downloadProgress: number | null;
        canStream: boolean;
        streamRequested: boolean;
        hlsFailed: boolean;
        streamMessage: string | null;
        eventsource: EventSource | null;
        keylistener: (e: KeyboardEvent) => void;
    }

    component<DownloadScreen>("download-screen", {
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
            preventchange: function (e: Event) {
                e.preventDefault();
                if (e.target instanceof HTMLInputElement) {
                    e.target.value = window.location.origin + (this.play_link || "");
                }
            },
            back: function () {
                window.history.back();
            },
            startStream: function () {
                var self = this;
                var magnet_hash = get_hash(this.params.magnet_link);
                self.streamRequested = true;
                self.streamMessage = null;
                post<StreamResponse | null>("/api/magnet/" + magnet_hash + "/" + encodeURIComponent(this.params.filename) + "/stream", {}, function (data) {
                    if (data && data.started) return;
                    // Backend declined — re-show ▶ and surface the reason so
                    // the user knows whether to retry, give up, or wait.
                    self.streamRequested = false;
                    var reasons: { [reason: string]: string } = {
                        disabled: "Streaming is disabled.",
                        unsupported_format: "This file format can't be streamed live.",
                        codec_failed: "Streaming failed for this file's codec.",
                        capacity: "Server is at streaming capacity. Try again shortly.",
                        not_ready: "Not enough data buffered yet — wait a moment.",
                        no_torrent: "Torrent isn't ready yet.",
                        file_not_found: "File not found in torrent.",
                        invalid_path: "Invalid filename.",
                    };
                    self.streamMessage = (data && data.reason && reasons[data.reason]) || "Couldn't start the stream.";
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
            var self = this;
            var magnet_hash = get_hash(this.params.magnet_link);
            function applyFileInfo(data: FileStatus) {
                self.status = data.status;
                self.progress = data.progress === undefined ? null : data.progress;
                var text = data.status.replace(/_/g, " ");
                self.heading =
                    data.progress === 0 || data.progress
                        ? text +
                          " (" +
                          String(Math.round(data.progress * 100)) +
                          "%)"
                        : text;
                var subheadingParts: string[] = [];
                if (data.source === "http") {
                    subheadingParts.push("HTTP");
                }
                if (data.peers === 0 || data.peers) {
                    subheadingParts.push(String(data.peers) + " Peers");
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
                    var hlsLink = "/play/" + magnet_hash + "/" + encodeURIComponent(data.hls_filename) + "?subs=" + String(hlsSubCount);
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
                    self.streamMessage = "Starting stream…";
                } else if (self.streamMessage === "Starting stream…") {
                    self.streamMessage = null;
                }
            }
            function pollFileInfo() {
                (function get_file_info() {
                    get<FileStatus>(
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
            this.eventsource = subscribe<FileStatus>(
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
        data: { screen: null as string | null, params: null as NavigoParams },
    });

    function display_view(view_name: string) {
        return function (params: NavigoParams) {
            clear_pending_requests();
            clear_pending_callbacks();

            var magnet_link = params && params["magnet_link"];
            if (params && magnet_link) {
                params["magnet_link"] = decodeURIComponent(decodeURIComponent(magnet_link));
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
