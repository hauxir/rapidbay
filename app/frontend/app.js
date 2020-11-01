(function() {
  window.isSafari = navigator.vendor && navigator.vendor.indexOf("Apple") > -1;
  window.isChrome = /Chrome/i.test(navigator.userAgent);

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
        isChrome: window.isChrome
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

  Vue.component("tree-view", {
    template: "#tree-view-template",
    props: {
      tree: [Object, String],
    },
    computed: {
      formatted_tree: function() {
        if (this.tree) {
          return this.create_tree(this.tree[""])
        }
        else return false;
      }
    },
    methods: {
      create_tree: function (folder_array, indent_level = 0) {
        let output_string = "";
        for (let item of folder_array) {
          if (typeof item == "string") {
            output_string += `|${'\t'.repeat(indent_level)}--${item}\n`;
          } else if (item instanceof Object) {
            Object.keys(item).forEach((key) => {
              output_string += `|${'\t'.repeat(indent_level)}--${key}\n`;
              indent_level += 1;
              output_string += this.create_tree(item[key], indent_level);
            });
            indent_level -= 2;
          }
        }
        return output_string;
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
    },
    created: function() {
      if (router.lastRouteResolved().url.toLowerCase() === "/registerhandler") {
        navigator.registerProtocolHandler(
          "magnet",
          router.root + "/magnet/%s",
          "RapidBay"
        );
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
        heading: "",
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
          if (!window.isSafari) {
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
          }
          if (self.status !== "ready") {
            rbsetTimeout(get_file_info, 1000);
          }
        });
      })();
    }
  });

  Vue.component("status-screen", {
    mixins: [rbmixin],
    template: "#status-screen-template",
    data: function() {
      return {
        status: {
        }
      };
    },
    created: function() {
      var self = this;
      get("/api/status", function(data) {
        self.status = data;
      })
    },
    computed: {
      output_dir_info: function () {
        return this.status.output_dir && this.status.output_dir.length !== 0 ? this.status.output_dir : null;
      },
      filelist_dir_info: function () {
        return this.status.filelist_dir && this.status.filelist_dir.length !== 0 ? this.status.filelist_dir : null;
      },
      downloads_dir_info: function () {
        return this.status.downloads_dir && this.status.downloads_dir.length !== 0 ? this.status.downloads_dir : null;
      },
      subtitle_downloads_info: function () {
        let subtitle_array = [];
        if (this.status.subtitle_downloads) {
          Object.keys(this.status.subtitle_downloads).forEach((key) => {
            subtitle_array.push(`${key}: ${this.status.subtitle_downloads[key]}`);
          });
        }
        return subtitle_array;
      },
      conversions_info: function () {
        let conversion_array = [];
        if (this.status.conversions) {
          Object.keys(this.status.conversions).forEach((key) => {
            conversion_array.push(key);
          });
        }
        return conversion_array;
      }
    },
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
      "dashboard": display_view("status-screen"),
      "*": display_view("search-screen"),
    })
    .resolve();
})();
