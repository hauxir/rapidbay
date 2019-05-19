(function() {
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
      pending_requests = pending_requests.filter(function(req) {
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

  var rbmixin = {
    props: ["params"],
    methods: {
      navigate: function(path) {
        router.navigate(path);
      }
    }
  };

  Vue.component("loading-spinner", {
    props: ["heading", "subheading", "progress"],
    template: "#loading-spinner-template",
    updated: function() {
      var progress_el = this.$refs.progress;
      progress_el && (progress_el.style.width = this.progress * 100 + "%");
    }
  });

  Vue.component("player", {
    props: ["url", "subtitles"],
    data: function() {
      return {
        isDesktop: !/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini|Mobile|mobile|CriOS/i.test(
          navigator.userAgent
        ),
        isChrome: /Chrome/i.test(navigator.userAgent)
      };
    },
    template: "#player-template"
  });

  Vue.component("chromecast-button", {
    template: "#chromecast-button-template",
    methods: {
      cast: function() {
        var root = window.location.origin;
        var video = document.getElementsByTagName("video")[0];
        var subtitle_tracks = Array.from(video.textTracks);
        var current_subtitle = subtitle_tracks.find(function(t) {
          return t.mode !== "disabled";
        });
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
                  src: current_subtitle_url
                }
              ]
            : []
        };
        var cc = new ChromecastJS();
        cc.cast(media);
      }
    }
  });

  Vue.component("search-screen", {
    template: "#search-screen-template",
    data: function() {
      return { searchterm: "" };
    },
    methods: {
      onSubmit: function(e) {
        e.preventDefault();
        if (this.searchterm.startsWith("magnet:")) {
          router.navigate(
            "/magnet/" + encodeURIComponent(encodeURIComponent(this.searchterm))
          );
        } else {
          router.navigate("/search/" + this.searchterm);
        }
      }
    }
  });

  Vue.component("search-results-screen", {
    mixins: [rbmixin],
    data: function() {
      return { results: null };
    },
    template: "#search-results-screen-template",
    created: function() {
      var self = this;
      get("/api/search/" + this.params.searchterm, function(data) {
        self.results = data.results;
      });
    }
  });

  Vue.component("filelist-screen", {
    mixins: [rbmixin],
    data: function() {
      return { results: null };
    },
    template: "#filelist-screen-template",
    created: function() {
      $.post("/api/magnet_files/", { magnet_link: this.params.magnet_link });
      var self = this;
      (function get_files() {
        get("/api/magnet/" + get_hash(self.params.magnet_link) + "/", function(
          data
        ) {
          if (data.files == null) {
            rbsetTimeout(get_files, 1000);
            return;
          }
          self.results = data.files;
        });
      })();
    }
  });

  Vue.component("download-screen", {
    mixins: [rbmixin],
    data: function() {
      return {
        progress: null,
        status: null,
        peers: null,
        heading: "Loading",
        subheading: null,
        play_link: null,
        subtitles: []
      };
    },
    template: "#download-screen-template",
    methods: {
      preventchange: function(e) {
        e.preventDefault();
        e.target.value = window.location.origin + this.play_link;
      }
    },
    created: function() {
      $.post("/api/magnet_download/", {
        magnet_link: this.params.magnet_link,
        filename: this.params.filename
      });
      var self = this;
      var magnet_hash = get_hash(this.params.magnet_link);
      (function get_file_info() {
        get("/api/magnet/" + magnet_hash + "/" + self.params.filename, function(
          data
        ) {
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
          self.subtitles = data.subtitles
            ? data.subtitles.map(function(sub) {
                return {
                  language: sub
                    .substring(sub.lastIndexOf("_") + 1)
                    .replace(".vtt", ""),
                  url: "/play/" + magnet_hash + "/" + sub
                };
              })
            : [];
          if (self.status !== "ready") {
            rbsetTimeout(get_file_info, 1000);
          }
        });
      })();
    }
  });

  var vm = new Vue({
    el: "#app",
    data: { screen: null, params: {} }
  });

  function display_view(view_name) {
    return function(params) {
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
      "search/:searchterm": display_view("search-results-screen"),
      "magnet/:magnet_link/": display_view("filelist-screen"),
      "magnet/:magnet_link/:filename": display_view("download-screen"),
      "*": display_view("search-screen")
    })
    .resolve();
})();
