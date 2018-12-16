function init_elements() {
  $(".loadingwrapper").hide();
  $(".filename")
    .html("")
    .hide();
  $("form").hide();
  $("table").hide();
  $(".progress-bar").width(0);
  $("tbody").html("");
  $(".videolink").hide();
  $(".progress").hide();
  $(".loadingtext").html("Loading");
  $(".peernum").html("");
  $(".peernum").hide();
  var id = window.setTimeout(function() {}, 0);
  while (id--) {
    window.clearTimeout(id); // will do nothing if no timeout with id is present
  }
}

function get_hash(magnet_link) {
  console.log(magnet_link);
  var hash_start = magnet_link.indexOf("btih:") + 5;
  var hash_end = magnet_link.indexOf("&");
  if (hash_end == -1) return magnet_link.substr(hash_start);
  return magnet_link.substr(hash_start, hash_end - hash_start);
}

var router = new Navigo(window.location.origin);
router
  .on({
    "search/:searchterm": function(params) {
      init_elements();
      $("table").show();
      $(".loadingwrapper").show();
      $("form").hide();
      $.get("/api/search/" + params.searchterm, function(data) {
        $("tbody").html("");
        data.results.forEach(function(result) {
          var tr = $("<tr><td>" + result.title + "</a></td></tr>");
          $(tr).click(function() {
            router.navigate(
              "/magnet/" +
                encodeURIComponent(encodeURIComponent(result.magnet)) +
                "/"
            );
          });
          $("tbody").append(tr);
        });
        $(".loadingwrapper").hide();
      }).fail(function() {
        $(".loadingwrapper").hide();
      });
    },
    "magnet/:magnet_link/": function(params) {
      params.magnet_link = decodeURIComponent(params.magnet_link);
      params.magnet_link = decodeURIComponent(params.magnet_link);
      init_elements();
      $("table").show();
      $(".loadingwrapper").show();
      $.post("/api/magnet_files/", { magnet_link: params.magnet_link });
      var get_files = function() {
        $.get("/api/magnet/" + get_hash(params.magnet_link) + "/", function(
          data
        ) {
          $("tbody").html("");
          if (data.files == null) {
            setTimeout(get_files, 1000);
            return;
          }
          $(".loadingwrapper").hide();
          data.files.forEach(function(file) {
            var tr = $("<tr><td>" + file + "</a></td></tr>");
            $(tr).click(function() {
              router.navigate(
                "/magnet/" +
                  encodeURIComponent(encodeURIComponent(params.magnet_link)) +
                  "/" +
                  file
              );
            });
            $("tbody").append(tr);
          });
          $(".loadingwrapper").hide();
        }).fail(function() {
          $(".loadingwrapper").hide();
        });
      };
      get_files();
    },
    "magnet/:magnet_link/:filename": function(params) {
      params.magnet_link = decodeURIComponent(params.magnet_link);
      params.magnet_link = decodeURIComponent(params.magnet_link);
      init_elements();
      $(".filename")
        .show()
        .html(params.filename);
      $.post("/api/magnet_download/", {
        magnet_link: params.magnet_link,
        filename: params.filename
      });
      var get_file_info = function() {
        $.get(
          "/api/magnet/" + get_hash(params.magnet_link) + "/" + params.filename,
          function(data) {
            var text = data.status.replace(/_/g, " ");
            if (data.status === "downloading" || data.status == "converting") {
              text = text + " (" + Math.round(data.progress * 100) + "%)";
              $(".progress").show();
              $(".progress-bar").width(data.progress * 100 + "%");
            } else {
              $(".peernum").hide();
              $(".progress").hide();
            }

            if (data.status === "downloading") {
              $(".peernum").html(data.peers + " Peers");
              $(".peernum").show();
            } else {
              $(".peernum")
                .html("")
                .hide();
            }
            if (data.status == "ready") {
              $(".loadingwrapper").hide();
              $(".videolink")
                .attr(
                  "href",
                  "/play/" +
                    get_hash(params.magnet_link) +
                    "/" +
                    params.filename
                )
                .show();
              return;
            }
            $(".loadingtext").html(text);
            setTimeout(get_file_info, 1000);
          }
        ).fail(function() {
          $(".loadingwrapper").hide();
        });
      };
      get_file_info();
      $(".loadingwrapper").show();
    },
    "*": function() {
      init_elements();
      $("form").show();
      $("input").focus();
    }
  })
  .resolve();

$("form").submit(function(event) {
  router.navigate("/search/" + $("input").val());
  event.preventDefault();
});
