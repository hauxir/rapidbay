(function() {
  function get_hash(magnet_link) {
    var hash_start = magnet_link.indexOf("btih:") + 5;
    var hash_end = magnet_link.indexOf("&");
    if (hash_end == -1) return magnet_link.substr(hash_start);
    return magnet_link.substr(hash_start, hash_end - hash_start);
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

  Vue.component("search-screen", {
    template: "#search-screen-template",
    data: function() {
      return { searchterm: "" };
    },
    methods: {
      onSubmit: function(e) {
        e.preventDefault();
        router.navigate("/search/" + this.searchterm);
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
      $.get("/api/search/" + this.params.searchterm, function(data) {
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
        $.get(
          "/api/magnet/" + get_hash(self.params.magnet_link) + "/",
          function(data) {
            if (data.files == null) {
              setTimeout(get_files, 1000);
              return;
            }
            self.results = data.files;
          }
        );
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
        play_link: null
      };
    },
    template: "#download-screen-template",
    created: function() {
      this.play_link =
        "/play/" +
        get_hash(this.params.magnet_link) +
        "/" +
        this.params.filename;
      $.post("/api/magnet_download/", {
        magnet_link: this.params.magnet_link,
        filename: this.params.filename
      });
      var self = this;
      (function get_file_info() {
        $.get(
          "/api/magnet/" +
            get_hash(self.params.magnet_link) +
            "/" +
            self.params.filename,
          function(data) {
            self.status = data.status;
            self.progress = data.progress;
            var text = data.status.replace(/_/g, " ");
            self.heading =
              data.progress === 0 || data.progress
                ? text + " (" + Math.round(data.progress * 100) + "%)"
                : text;
            self.subheading =
              data.peers === 0 || data.peers ? data.peers + " Peers" : null;
            if (self.status !== "ready") {
              setTimeout(get_file_info, 1000);
            }
          }
        );
      })();
    }
  });

  var vm = new Vue({
    el: "#app",
    data: { screen: null, params: {} }
  });

  function display_view(view_name) {
    return function(params) {
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
