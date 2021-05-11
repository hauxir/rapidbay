function _objectWithoutProperties(source, excluded) { if (source == null) return {}; var target = _objectWithoutPropertiesLoose(source, excluded); var key, i; if (Object.getOwnPropertySymbols) { var sourceSymbolKeys = Object.getOwnPropertySymbols(source); for (i = 0; i < sourceSymbolKeys.length; i++) { key = sourceSymbolKeys[i]; if (excluded.indexOf(key) >= 0) continue; if (!Object.prototype.propertyIsEnumerable.call(source, key)) continue; target[key] = source[key]; } } return target; }

function _objectWithoutPropertiesLoose(source, excluded) { if (source == null) return {}; var target = {}; var sourceKeys = Object.keys(source); var key, i; for (i = 0; i < sourceKeys.length; i++) { key = sourceKeys[i]; if (excluded.indexOf(key) >= 0) continue; target[key] = source[key]; } return target; }

function _toConsumableArray(arr) { return _arrayWithoutHoles(arr) || _iterableToArray(arr) || _unsupportedIterableToArray(arr) || _nonIterableSpread(); }

function _nonIterableSpread() { throw new TypeError("Invalid attempt to spread non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method."); }

function _iterableToArray(iter) { if (typeof Symbol !== "undefined" && iter[Symbol.iterator] != null || iter["@@iterator"] != null) return Array.from(iter); }

function _arrayWithoutHoles(arr) { if (Array.isArray(arr)) return _arrayLikeToArray(arr); }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); return Constructor; }

function ownKeys(object, enumerableOnly) { var keys = Object.keys(object); if (Object.getOwnPropertySymbols) { var symbols = Object.getOwnPropertySymbols(object); if (enumerableOnly) { symbols = symbols.filter(function (sym) { return Object.getOwnPropertyDescriptor(object, sym).enumerable; }); } keys.push.apply(keys, symbols); } return keys; }

function _objectSpread(target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i] != null ? arguments[i] : {}; if (i % 2) { ownKeys(Object(source), true).forEach(function (key) { _defineProperty(target, key, source[key]); }); } else if (Object.getOwnPropertyDescriptors) { Object.defineProperties(target, Object.getOwnPropertyDescriptors(source)); } else { ownKeys(Object(source)).forEach(function (key) { Object.defineProperty(target, key, Object.getOwnPropertyDescriptor(source, key)); }); } } return target; }

function _slicedToArray(arr, i) { return _arrayWithHoles(arr) || _iterableToArrayLimit(arr, i) || _unsupportedIterableToArray(arr, i) || _nonIterableRest(); }

function _nonIterableRest() { throw new TypeError("Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method."); }

function _unsupportedIterableToArray(o, minLen) { if (!o) return; if (typeof o === "string") return _arrayLikeToArray(o, minLen); var n = Object.prototype.toString.call(o).slice(8, -1); if (n === "Object" && o.constructor) n = o.constructor.name; if (n === "Map" || n === "Set") return Array.from(o); if (n === "Arguments" || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)) return _arrayLikeToArray(o, minLen); }

function _arrayLikeToArray(arr, len) { if (len == null || len > arr.length) len = arr.length; for (var i = 0, arr2 = new Array(len); i < len; i++) { arr2[i] = arr[i]; } return arr2; }

function _iterableToArrayLimit(arr, i) { var _i = arr && (typeof Symbol !== "undefined" && arr[Symbol.iterator] || arr["@@iterator"]); if (_i == null) return; var _arr = []; var _n = true; var _d = false; var _s, _e; try { for (_i = _i.call(arr); !(_n = (_s = _i.next()).done); _n = true) { _arr.push(_s.value); if (i && _arr.length === i) break; } } catch (err) { _d = true; _e = err; } finally { try { if (!_n && _i["return"] != null) _i["return"](); } finally { if (_d) throw _e; } } return _arr; }

function _arrayWithHoles(arr) { if (Array.isArray(arr)) return arr; }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

function _typeof(obj) { "@babel/helpers - typeof"; if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") { _typeof = function _typeof(obj) { return typeof obj; }; } else { _typeof = function _typeof(obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }; } return _typeof(obj); }

"object" == (typeof navigator === "undefined" ? "undefined" : _typeof(navigator)) && function (e, t) {
  "object" == (typeof exports === "undefined" ? "undefined" : _typeof(exports)) && "undefined" != typeof module ? module.exports = t() : "function" == typeof define && define.amd ? define("Plyr", t) : (e = "undefined" != typeof globalThis ? globalThis : e || self).Plyr = t();
}(this, function () {
  "use strict";

  function e(e, t, i) {
    return t in e ? Object.defineProperty(e, t, {
      value: i,
      enumerable: !0,
      configurable: !0,
      writable: !0
    }) : e[t] = i, e;
  }

  function t(e, t) {
    for (var i = 0; i < t.length; i++) {
      var s = t[i];
      s.enumerable = s.enumerable || !1, s.configurable = !0, "value" in s && (s.writable = !0), Object.defineProperty(e, s.key, s);
    }
  }

  function i(e, t, i) {
    return t in e ? Object.defineProperty(e, t, {
      value: i,
      enumerable: !0,
      configurable: !0,
      writable: !0
    }) : e[t] = i, e;
  }

  function s(e, t) {
    var i = Object.keys(e);

    if (Object.getOwnPropertySymbols) {
      var s = Object.getOwnPropertySymbols(e);
      t && (s = s.filter(function (t) {
        return Object.getOwnPropertyDescriptor(e, t).enumerable;
      })), i.push.apply(i, s);
    }

    return i;
  }

  function n(e) {
    for (var t = 1; t < arguments.length; t++) {
      var n = null != arguments[t] ? arguments[t] : {};
      t % 2 ? s(Object(n), !0).forEach(function (t) {
        i(e, t, n[t]);
      }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(n)) : s(Object(n)).forEach(function (t) {
        Object.defineProperty(e, t, Object.getOwnPropertyDescriptor(n, t));
      });
    }

    return e;
  }

  var a = {
    addCSS: !0,
    thumbWidth: 15,
    watch: !0
  };

  function l(e, t) {
    return function () {
      return Array.from(document.querySelectorAll(t)).includes(this);
    }.call(e, t);
  }

  var o = function o(e) {
    return null != e ? e.constructor : null;
  },
      r = function r(e, t) {
    return !!(e && t && e instanceof t);
  },
      c = function c(e) {
    return null == e;
  },
      h = function h(e) {
    return o(e) === Object;
  },
      u = function u(e) {
    return o(e) === String;
  },
      d = function d(e) {
    return Array.isArray(e);
  },
      m = function m(e) {
    return r(e, NodeList);
  },
      p = u,
      g = d,
      f = m,
      b = function b(e) {
    return r(e, Element);
  },
      y = function y(e) {
    return r(e, Event);
  },
      v = function v(e) {
    return c(e) || (u(e) || d(e) || m(e)) && !e.length || h(e) && !Object.keys(e).length;
  };

  function w(e, t) {
    if (1 > t) {
      var i = function (e) {
        var t = "".concat(e).match(/(?:\.(\d+))?(?:[eE]([+-]?\d+))?$/);
        return t ? Math.max(0, (t[1] ? t[1].length : 0) - (t[2] ? +t[2] : 0)) : 0;
      }(t);

      return parseFloat(e.toFixed(i));
    }

    return Math.round(e / t) * t;
  }

  var T = function () {
    function e(t, i) {
      (function (e, t) {
        if (!(e instanceof t)) throw new TypeError("Cannot call a class as a function");
      })(this, e), b(t) ? this.element = t : p(t) && (this.element = document.querySelector(t)), b(this.element) && v(this.element.rangeTouch) && (this.config = n({}, a, {}, i), this.init());
    }

    return function (e, i, s) {
      i && t(e.prototype, i), s && t(e, s);
    }(e, [{
      key: "init",
      value: function value() {
        e.enabled && (this.config.addCSS && (this.element.style.userSelect = "none", this.element.style.webKitUserSelect = "none", this.element.style.touchAction = "manipulation"), this.listeners(!0), this.element.rangeTouch = this);
      }
    }, {
      key: "destroy",
      value: function value() {
        e.enabled && (this.config.addCSS && (this.element.style.userSelect = "", this.element.style.webKitUserSelect = "", this.element.style.touchAction = ""), this.listeners(!1), this.element.rangeTouch = null);
      }
    }, {
      key: "listeners",
      value: function value(e) {
        var t = this,
            i = e ? "addEventListener" : "removeEventListener";
        ["touchstart", "touchmove", "touchend"].forEach(function (e) {
          t.element[i](e, function (e) {
            return t.set(e);
          }, !1);
        });
      }
    }, {
      key: "get",
      value: function value(t) {
        if (!e.enabled || !y(t)) return null;
        var i,
            s = t.target,
            n = t.changedTouches[0],
            a = parseFloat(s.getAttribute("min")) || 0,
            l = parseFloat(s.getAttribute("max")) || 100,
            o = parseFloat(s.getAttribute("step")) || 1,
            r = s.getBoundingClientRect(),
            c = 100 / r.width * (this.config.thumbWidth / 2) / 100;
        return 0 > (i = 100 / r.width * (n.clientX - r.left)) ? i = 0 : 100 < i && (i = 100), 50 > i ? i -= (100 - 2 * i) * c : 50 < i && (i += 2 * (i - 50) * c), a + w(i / 100 * (l - a), o);
      }
    }, {
      key: "set",
      value: function value(t) {
        e.enabled && y(t) && !t.target.disabled && (t.preventDefault(), t.target.value = this.get(t), function (e, t) {
          if (e && t) {
            var i = new Event(t, {
              bubbles: !0
            });
            e.dispatchEvent(i);
          }
        }(t.target, "touchend" === t.type ? "change" : "input"));
      }
    }], [{
      key: "setup",
      value: function value(t) {
        var i = 1 < arguments.length && void 0 !== arguments[1] ? arguments[1] : {},
            s = null;
        if (v(t) || p(t) ? s = Array.from(document.querySelectorAll(p(t) ? t : 'input[type="range"]')) : b(t) ? s = [t] : f(t) ? s = Array.from(t) : g(t) && (s = t.filter(b)), v(s)) return null;
        var o = n({}, a, {}, i);

        if (p(t) && o.watch) {
          var r = new MutationObserver(function (i) {
            Array.from(i).forEach(function (i) {
              Array.from(i.addedNodes).forEach(function (i) {
                b(i) && l(i, t) && new e(i, o);
              });
            });
          });
          r.observe(document.body, {
            childList: !0,
            subtree: !0
          });
        }

        return s.map(function (t) {
          return new e(t, i);
        });
      }
    }, {
      key: "enabled",
      get: function get() {
        return "ontouchstart" in document.documentElement;
      }
    }]), e;
  }();

  var k = function k(e) {
    return null != e ? e.constructor : null;
  },
      C = function C(e, t) {
    return Boolean(e && t && e instanceof t);
  },
      A = function A(e) {
    return null == e;
  },
      S = function S(e) {
    return k(e) === Object;
  },
      E = function E(e) {
    return k(e) === String;
  },
      P = function P(e) {
    return k(e) === Function;
  },
      N = function N(e) {
    return Array.isArray(e);
  },
      M = function M(e) {
    return C(e, NodeList);
  },
      x = function x(e) {
    return A(e) || (E(e) || N(e) || M(e)) && !e.length || S(e) && !Object.keys(e).length;
  };

  var I = A,
      L = S,
      $ = function $(e) {
    return k(e) === Number && !Number.isNaN(e);
  },
      _ = E,
      O = function O(e) {
    return k(e) === Boolean;
  },
      q = P,
      j = N,
      D = M,
      H = function H(e) {
    return null !== e && "object" == _typeof(e) && 1 === e.nodeType && "object" == _typeof(e.style) && "object" == _typeof(e.ownerDocument);
  },
      F = function F(e) {
    return C(e, Event);
  },
      R = function R(e) {
    return C(e, KeyboardEvent);
  },
      V = function V(e) {
    return C(e, TextTrack) || !A(e) && E(e.kind);
  },
      B = function B(e) {
    return C(e, Promise) && P(e.then);
  },
      U = function U(e) {
    if (C(e, window.URL)) return !0;
    if (!E(e)) return !1;
    var t = e;
    e.startsWith("http://") && e.startsWith("https://") || (t = "http://".concat(e));

    try {
      return !x(new URL(t).hostname);
    } catch (e) {
      return !1;
    }
  },
      W = x;

  var z = function () {
    var e = document.createElement("span"),
        t = {
      WebkitTransition: "webkitTransitionEnd",
      MozTransition: "transitionend",
      OTransition: "oTransitionEnd otransitionend",
      transition: "transitionend"
    },
        i = Object.keys(t).find(function (t) {
      return void 0 !== e.style[t];
    });
    return !!_(i) && t[i];
  }();

  function K(e, t) {
    setTimeout(function () {
      try {
        e.hidden = !0, e.offsetHeight, e.hidden = !1;
      } catch (e) {}
    }, t);
  }

  var Y = {
    isIE: Boolean(window.document.documentMode),
    isEdge: window.navigator.userAgent.includes("Edge"),
    isWebkit: "WebkitAppearance" in document.documentElement.style && !/Edge/.test(navigator.userAgent),
    isIPhone: /(iPhone|iPod)/gi.test(navigator.platform),
    isIos: /(iPad|iPhone|iPod)/gi.test(navigator.platform)
  };

  function Q(e, t) {
    return t.split(".").reduce(function (e, t) {
      return e && e[t];
    }, e);
  }

  function X() {
    var e = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : {};

    for (var _len = arguments.length, t = new Array(_len > 1 ? _len - 1 : 0), _key = 1; _key < _len; _key++) {
      t[_key - 1] = arguments[_key];
    }

    if (!t.length) return e;
    var i = t.shift();
    return L(i) ? (Object.keys(i).forEach(function (t) {
      L(i[t]) ? (Object.keys(e).includes(t) || Object.assign(e, _defineProperty({}, t, {})), X(e[t], i[t])) : Object.assign(e, _defineProperty({}, t, i[t]));
    }), X.apply(void 0, [e].concat(t))) : e;
  }

  function J(e, t) {
    var i = e.length ? e : [e];
    Array.from(i).reverse().forEach(function (e, i) {
      var s = i > 0 ? t.cloneNode(!0) : t,
          n = e.parentNode,
          a = e.nextSibling;
      s.appendChild(e), a ? n.insertBefore(s, a) : n.appendChild(s);
    });
  }

  function G(e, t) {
    H(e) && !W(t) && Object.entries(t).filter(function (_ref) {
      var _ref2 = _slicedToArray(_ref, 2),
          e = _ref2[1];

      return !I(e);
    }).forEach(function (_ref3) {
      var _ref4 = _slicedToArray(_ref3, 2),
          t = _ref4[0],
          i = _ref4[1];

      return e.setAttribute(t, i);
    });
  }

  function Z(e, t, i) {
    var s = document.createElement(e);
    return L(t) && G(s, t), _(i) && (s.innerText = i), s;
  }

  function ee(e, t, i, s) {
    H(t) && t.appendChild(Z(e, i, s));
  }

  function te(e) {
    D(e) || j(e) ? Array.from(e).forEach(te) : H(e) && H(e.parentNode) && e.parentNode.removeChild(e);
  }

  function ie(e) {
    if (!H(e)) return;
    var t = e.childNodes.length;

    for (; t > 0;) {
      e.removeChild(e.lastChild), t -= 1;
    }
  }

  function se(e, t) {
    return H(t) && H(t.parentNode) && H(e) ? (t.parentNode.replaceChild(e, t), e) : null;
  }

  function ne(e, t) {
    if (!_(e) || W(e)) return {};
    var i = {},
        s = X({}, t);
    return e.split(",").forEach(function (e) {
      var t = e.trim(),
          n = t.replace(".", ""),
          a = t.replace(/[[\]]/g, "").split("="),
          _a = _slicedToArray(a, 1),
          l = _a[0],
          o = a.length > 1 ? a[1].replace(/["']/g, "") : "";

      switch (t.charAt(0)) {
        case ".":
          _(s.class) ? i.class = "".concat(s.class, " ").concat(n) : i.class = n;
          break;

        case "#":
          i.id = t.replace("#", "");
          break;

        case "[":
          i[l] = o;
      }
    }), X(s, i);
  }

  function ae(e, t) {
    if (!H(e)) return;
    var i = t;
    O(i) || (i = !e.hidden), e.hidden = i;
  }

  function le(e, t, i) {
    if (D(e)) return Array.from(e).map(function (e) {
      return le(e, t, i);
    });

    if (H(e)) {
      var _s2 = "toggle";
      return void 0 !== i && (_s2 = i ? "add" : "remove"), e.classList[_s2](t), e.classList.contains(t);
    }

    return !1;
  }

  function oe(e, t) {
    return H(e) && e.classList.contains(t);
  }

  function re(e, t) {
    var _Element = Element,
        i = _Element.prototype;
    return (i.matches || i.webkitMatchesSelector || i.mozMatchesSelector || i.msMatchesSelector || function () {
      return Array.from(document.querySelectorAll(t)).includes(this);
    }).call(e, t);
  }

  function ce(e) {
    return this.elements.container.querySelectorAll(e);
  }

  function he(e) {
    return this.elements.container.querySelector(e);
  }

  function ue() {
    var e = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : null;
    var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : !1;
    H(e) && (e.focus({
      preventScroll: !0
    }), t && le(e, this.config.classNames.tabFocus));
  }

  var de = {
    "audio/ogg": "vorbis",
    "audio/wav": "1",
    "video/webm": "vp8, vorbis",
    "video/mp4": "avc1.42E01E, mp4a.40.2",
    "video/ogg": "theora"
  },
      me = {
    audio: "canPlayType" in document.createElement("audio"),
    video: "canPlayType" in document.createElement("video"),
    check: function check(e, t, i) {
      var s = Y.isIPhone && i && me.playsinline,
          n = me[e] || "html5" !== t;
      return {
        api: n,
        ui: n && me.rangeInput && ("video" !== e || !Y.isIPhone || s)
      };
    },
    pip: !(Y.isIPhone || !q(Z("video").webkitSetPresentationMode) && (!document.pictureInPictureEnabled || Z("video").disablePictureInPicture)),
    airplay: q(window.WebKitPlaybackTargetAvailabilityEvent),
    playsinline: "playsInline" in document.createElement("video"),
    mime: function mime(e) {
      if (W(e)) return !1;

      var _e$split = e.split("/"),
          _e$split2 = _slicedToArray(_e$split, 1),
          t = _e$split2[0];

      var i = e;
      if (!this.isHTML5 || t !== this.type) return !1;
      Object.keys(de).includes(i) && (i += "; codecs=\"".concat(de[e], "\""));

      try {
        return Boolean(i && this.media.canPlayType(i).replace(/no/, ""));
      } catch (e) {
        return !1;
      }
    },
    textTracks: "textTracks" in document.createElement("video"),
    rangeInput: function () {
      var e = document.createElement("input");
      return e.type = "range", "range" === e.type;
    }(),
    touch: "ontouchstart" in document.documentElement,
    transitions: !1 !== z,
    reducedMotion: "matchMedia" in window && window.matchMedia("(prefers-reduced-motion)").matches
  },
      pe = function () {
    var e = !1;

    try {
      var _t = Object.defineProperty({}, "passive", {
        get: function get() {
          return e = !0, null;
        }
      });

      window.addEventListener("test", null, _t), window.removeEventListener("test", null, _t);
    } catch (e) {}

    return e;
  }();

  function ge(e, t, i) {
    var _this = this;

    var s = arguments.length > 3 && arguments[3] !== undefined ? arguments[3] : !1;
    var n = arguments.length > 4 && arguments[4] !== undefined ? arguments[4] : !0;
    var a = arguments.length > 5 && arguments[5] !== undefined ? arguments[5] : !1;
    if (!e || !("addEventListener" in e) || W(t) || !q(i)) return;
    var l = t.split(" ");
    var o = a;
    pe && (o = {
      passive: n,
      capture: a
    }), l.forEach(function (t) {
      _this && _this.eventListeners && s && _this.eventListeners.push({
        element: e,
        type: t,
        callback: i,
        options: o
      }), e[s ? "addEventListener" : "removeEventListener"](t, i, o);
    });
  }

  function fe(e) {
    var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : "";
    var i = arguments.length > 2 ? arguments[2] : undefined;
    var s = arguments.length > 3 && arguments[3] !== undefined ? arguments[3] : !0;
    var n = arguments.length > 4 && arguments[4] !== undefined ? arguments[4] : !1;
    ge.call(this, e, t, i, !0, s, n);
  }

  function be(e) {
    var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : "";
    var i = arguments.length > 2 ? arguments[2] : undefined;
    var s = arguments.length > 3 && arguments[3] !== undefined ? arguments[3] : !0;
    var n = arguments.length > 4 && arguments[4] !== undefined ? arguments[4] : !1;
    ge.call(this, e, t, i, !1, s, n);
  }

  function ye(e) {
    var _this2 = this;

    var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : "";
    var i = arguments.length > 2 ? arguments[2] : undefined;
    var s = arguments.length > 3 && arguments[3] !== undefined ? arguments[3] : !0;
    var n = arguments.length > 4 && arguments[4] !== undefined ? arguments[4] : !1;

    var a = function a() {
      for (var _len2 = arguments.length, l = new Array(_len2), _key2 = 0; _key2 < _len2; _key2++) {
        l[_key2] = arguments[_key2];
      }

      be(e, t, a, s, n), i.apply(_this2, l);
    };

    ge.call(this, e, t, a, !0, s, n);
  }

  function ve(e) {
    var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : "";
    var i = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : !1;
    var s = arguments.length > 3 && arguments[3] !== undefined ? arguments[3] : {};
    if (!H(e) || W(t)) return;
    var n = new CustomEvent(t, {
      bubbles: i,
      detail: _objectSpread(_objectSpread({}, s), {}, {
        plyr: this
      })
    });
    e.dispatchEvent(n);
  }

  function we() {
    this && this.eventListeners && (this.eventListeners.forEach(function (e) {
      var t = e.element,
          i = e.type,
          s = e.callback,
          n = e.options;
      t.removeEventListener(i, s, n);
    }), this.eventListeners = []);
  }

  function Te() {
    var _this3 = this;

    return new Promise(function (e) {
      return _this3.ready ? setTimeout(e, 0) : fe.call(_this3, _this3.elements.container, "ready", e);
    }).then(function () {});
  }

  function ke(e) {
    B(e) && e.then(null, function () {});
  }

  function Ce(e) {
    return j(e) ? e.filter(function (t, i) {
      return e.indexOf(t) === i;
    }) : e;
  }

  function Ae(e, t) {
    return j(e) && e.length ? e.reduce(function (e, i) {
      return Math.abs(i - t) < Math.abs(e - t) ? i : e;
    }) : null;
  }

  var Se = [[1, 1], [4, 3], [3, 4], [5, 4], [4, 5], [3, 2], [2, 3], [16, 10], [10, 16], [16, 9], [9, 16], [21, 9], [9, 21], [32, 9], [9, 32]].reduce(function (e, _ref5) {
    var _ref6 = _slicedToArray(_ref5, 2),
        t = _ref6[0],
        i = _ref6[1];

    return _objectSpread(_objectSpread({}, e), {}, _defineProperty({}, t / i, [t, i]));
  }, {});

  function Ee(e) {
    if (!(j(e) || _(e) && e.includes(":"))) return !1;
    return (j(e) ? e : e.split(":")).map(Number).every($);
  }

  function Pe(e) {
    if (!j(e) || !e.every($)) return null;

    var _e2 = _slicedToArray(e, 2),
        t = _e2[0],
        i = _e2[1],
        s = function s(e, t) {
      return 0 === t ? e : s(t, e % t);
    },
        n = s(t, i);

    return [t / n, i / n];
  }

  function Ne(e) {
    var _this$embed;

    var t = function t(e) {
      return Ee(e) ? e.split(":").map(Number) : null;
    };

    var i = t(e);

    if (null === i && (i = t(this.config.ratio)), null === i && !W(this.embed) && j(this.embed.ratio) && (_this$embed = this.embed, i = _this$embed.ratio, _this$embed), null === i && this.isHTML5) {
      var _this$media = this.media,
          _e3 = _this$media.videoWidth,
          _t2 = _this$media.videoHeight;
      i = Pe([_e3, _t2]);
    }

    return i;
  }

  function Me(e) {
    if (!this.isVideo) return {};
    var t = this.elements.wrapper,
        i = Ne.call(this, e);
    if (!j(i)) return {};

    var _i2 = _slicedToArray(i, 2),
        s = _i2[0],
        n = _i2[1],
        a = 100 / s * n;

    if (!!window.CSS && window.CSS.supports("aspect-ratio: ".concat(s, "/").concat(n)) ? t.style.aspectRatio = "".concat(s, "/").concat(n) : t.style.paddingBottom = "".concat(a, "%"), this.isVimeo && !this.config.vimeo.premium && this.supported.ui) {
      var _e4 = 100 / this.media.offsetWidth * parseInt(window.getComputedStyle(this.media).paddingBottom, 10),
          _i3 = (_e4 - a) / (_e4 / 50);

      this.fullscreen.active ? t.style.paddingBottom = null : this.media.style.transform = "translateY(-".concat(_i3, "%)");
    } else this.isHTML5 && t.classList.toggle(this.config.classNames.videoFixedRatio, null !== i);

    return {
      padding: a,
      ratio: i
    };
  }

  function xe(e, t) {
    var i = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : .05;
    var s = e / t,
        n = Ae(Object.keys(Se), s);
    return Math.abs(n - s) <= i ? Se[n] : [e, t];
  }

  var Ie = {
    getSources: function getSources() {
      var _this4 = this;

      if (!this.isHTML5) return [];
      return Array.from(this.media.querySelectorAll("source")).filter(function (e) {
        var t = e.getAttribute("type");
        return !!W(t) || me.mime.call(_this4, t);
      });
    },
    getQualityOptions: function getQualityOptions() {
      return this.config.quality.forced ? this.config.quality.options : Ie.getSources.call(this).map(function (e) {
        return Number(e.getAttribute("size"));
      }).filter(Boolean);
    },
    setup: function setup() {
      if (!this.isHTML5) return;
      var e = this;
      e.options.speed = e.config.speed.options, W(this.config.ratio) || Me.call(e), Object.defineProperty(e.media, "quality", {
        get: function get() {
          var t = Ie.getSources.call(e).find(function (t) {
            return t.getAttribute("src") === e.source;
          });
          return t && Number(t.getAttribute("size"));
        },
        set: function set(t) {
          if (e.quality !== t) {
            if (e.config.quality.forced && q(e.config.quality.onChange)) e.config.quality.onChange(t);else {
              var _i4 = Ie.getSources.call(e).find(function (e) {
                return Number(e.getAttribute("size")) === t;
              });

              if (!_i4) return;
              var _e$media = e.media,
                  _s3 = _e$media.currentTime,
                  _n2 = _e$media.paused,
                  _a2 = _e$media.preload,
                  _l = _e$media.readyState,
                  _o = _e$media.playbackRate;
              e.media.src = _i4.getAttribute("src"), ("none" !== _a2 || _l) && (e.once("loadedmetadata", function () {
                e.speed = _o, e.currentTime = _s3, _n2 || ke(e.play());
              }), e.media.load());
            }
            ve.call(e, e.media, "qualitychange", !1, {
              quality: t
            });
          }
        }
      });
    },
    cancelRequests: function cancelRequests() {
      this.isHTML5 && (te(Ie.getSources.call(this)), this.media.setAttribute("src", this.config.blankVideo), this.media.load(), this.debug.log("Cancelled network requests"));
    }
  };

  function Le(e) {
    for (var _len3 = arguments.length, t = new Array(_len3 > 1 ? _len3 - 1 : 0), _key3 = 1; _key3 < _len3; _key3++) {
      t[_key3 - 1] = arguments[_key3];
    }

    return W(e) ? e : e.toString().replace(/{(\d+)}/g, function (e, i) {
      return t[i].toString();
    });
  }

  var $e = function $e() {
    var e = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : "";
    var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : "";
    var i = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : "";
    return e.replace(new RegExp(t.toString().replace(/([.*+?^=!:${}()|[\]/\\])/g, "\\$1"), "g"), i.toString());
  },
      _e = function _e() {
    var e = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : "";
    return e.toString().replace(/\w\S*/g, function (e) {
      return e.charAt(0).toUpperCase() + e.substr(1).toLowerCase();
    });
  };

  function Oe() {
    var e = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : "";
    var t = e.toString();
    return t = function () {
      var e = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : "";
      var t = e.toString();
      return t = $e(t, "-", " "), t = $e(t, "_", " "), t = _e(t), $e(t, " ", "");
    }(t), t.charAt(0).toLowerCase() + t.slice(1);
  }

  function qe(e) {
    var t = document.createElement("div");
    return t.appendChild(e), t.innerHTML;
  }

  var je = {
    pip: "PIP",
    airplay: "AirPlay",
    html5: "HTML5",
    vimeo: "Vimeo",
    youtube: "YouTube"
  },
      De = {
    get: function get() {
      var e = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : "";
      var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : {};
      if (W(e) || W(t)) return "";
      var i = Q(t.i18n, e);
      if (W(i)) return Object.keys(je).includes(e) ? je[e] : "";
      var s = {
        "{seektime}": t.seekTime,
        "{title}": t.title
      };
      return Object.entries(s).forEach(function (_ref7) {
        var _ref8 = _slicedToArray(_ref7, 2),
            e = _ref8[0],
            t = _ref8[1];

        i = $e(i, e, t);
      }), i;
    }
  };

  var He = /*#__PURE__*/function () {
    function He(t) {
      var _this5 = this;

      _classCallCheck(this, He);

      e(this, "get", function (e) {
        if (!He.supported || !_this5.enabled) return null;
        var t = window.localStorage.getItem(_this5.key);
        if (W(t)) return null;
        var i = JSON.parse(t);
        return _(e) && e.length ? i[e] : i;
      }), e(this, "set", function (e) {
        if (!He.supported || !_this5.enabled) return;
        if (!L(e)) return;

        var t = _this5.get();

        W(t) && (t = {}), X(t, e), window.localStorage.setItem(_this5.key, JSON.stringify(t));
      }), this.enabled = t.config.storage.enabled, this.key = t.config.storage.key;
    }

    _createClass(He, null, [{
      key: "supported",
      get: function get() {
        try {
          if (!("localStorage" in window)) return !1;
          var _e5 = "___test";
          return window.localStorage.setItem(_e5, _e5), window.localStorage.removeItem(_e5), !0;
        } catch (e) {
          return !1;
        }
      }
    }]);

    return He;
  }();

  function Fe(e) {
    var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : "text";
    return new Promise(function (i, s) {
      try {
        var _s4 = new XMLHttpRequest();

        if (!("withCredentials" in _s4)) return;
        _s4.addEventListener("load", function () {
          if ("text" === t) try {
            i(JSON.parse(_s4.responseText));
          } catch (e) {
            i(_s4.responseText);
          } else i(_s4.response);
        }), _s4.addEventListener("error", function () {
          throw new Error(_s4.status);
        }), _s4.open("GET", e, !0), _s4.responseType = t, _s4.send();
      } catch (e) {
        s(e);
      }
    });
  }

  function Re(e, t) {
    if (!_(e)) return;

    var i = _(t);

    var s = !1;

    var n = function n() {
      return null !== document.getElementById(t);
    },
        a = function a(e, t) {
      e.innerHTML = t, i && n() || document.body.insertAdjacentElement("afterbegin", e);
    };

    if (!i || !n()) {
      var _n3 = He.supported,
          _l2 = document.createElement("div");

      if (_l2.setAttribute("hidden", ""), i && _l2.setAttribute("id", t), _n3) {
        var _e6 = window.localStorage.getItem("cache-".concat(t));

        if (s = null !== _e6, s) {
          var _t3 = JSON.parse(_e6);

          a(_l2, _t3.content);
        }
      }

      Fe(e).then(function (e) {
        W(e) || (_n3 && window.localStorage.setItem("cache-".concat(t), JSON.stringify({
          content: e
        })), a(_l2, e));
      }).catch(function () {});
    }
  }

  var Ve = function Ve(e) {
    return Math.trunc(e / 60 / 60 % 60, 10);
  };

  function Be() {
    var e = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : 0;
    var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : !1;
    var i = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : !1;
    if (!$(e)) return Be(void 0, t, i);

    var s = function s(e) {
      return "0".concat(e).slice(-2);
    };

    var n = Ve(e);
    var a = (l = e, Math.trunc(l / 60 % 60, 10));
    var l;

    var o = function (e) {
      return Math.trunc(e % 60, 10);
    }(e);

    return n = t || n > 0 ? "".concat(n, ":") : "", "".concat(i && e > 0 ? "-" : "").concat(n).concat(s(a), ":").concat(s(o));
  }

  var Ue = {
    getIconUrl: function getIconUrl() {
      var e = new URL(this.config.iconUrl, window.location).host !== window.location.host || Y.isIE && !window.svg4everybody;
      return {
        url: this.config.iconUrl,
        cors: e
      };
    },
    findElements: function findElements() {
      try {
        return this.elements.controls = he.call(this, this.config.selectors.controls.wrapper), this.elements.buttons = {
          play: ce.call(this, this.config.selectors.buttons.play),
          pause: he.call(this, this.config.selectors.buttons.pause),
          restart: he.call(this, this.config.selectors.buttons.restart),
          rewind: he.call(this, this.config.selectors.buttons.rewind),
          fastForward: he.call(this, this.config.selectors.buttons.fastForward),
          mute: he.call(this, this.config.selectors.buttons.mute),
          pip: he.call(this, this.config.selectors.buttons.pip),
          airplay: he.call(this, this.config.selectors.buttons.airplay),
          settings: he.call(this, this.config.selectors.buttons.settings),
          captions: he.call(this, this.config.selectors.buttons.captions),
          fullscreen: he.call(this, this.config.selectors.buttons.fullscreen)
        }, this.elements.progress = he.call(this, this.config.selectors.progress), this.elements.inputs = {
          seek: he.call(this, this.config.selectors.inputs.seek),
          volume: he.call(this, this.config.selectors.inputs.volume)
        }, this.elements.display = {
          buffer: he.call(this, this.config.selectors.display.buffer),
          currentTime: he.call(this, this.config.selectors.display.currentTime),
          duration: he.call(this, this.config.selectors.display.duration)
        }, H(this.elements.progress) && (this.elements.display.seekTooltip = this.elements.progress.querySelector(".".concat(this.config.classNames.tooltip))), !0;
      } catch (e) {
        return this.debug.warn("It looks like there is a problem with your custom controls HTML", e), this.toggleNativeControls(!0), !1;
      }
    },
    createIcon: function createIcon(e, t) {
      var i = "http://www.w3.org/2000/svg",
          s = Ue.getIconUrl.call(this),
          n = "".concat(s.cors ? "" : s.url, "#").concat(this.config.iconPrefix),
          a = document.createElementNS(i, "svg");
      G(a, X(t, {
        "aria-hidden": "true",
        focusable: "false"
      }));
      var l = document.createElementNS(i, "use"),
          o = "".concat(n, "-").concat(e);
      return "href" in l && l.setAttributeNS("http://www.w3.org/1999/xlink", "href", o), l.setAttributeNS("http://www.w3.org/1999/xlink", "xlink:href", o), a.appendChild(l), a;
    },
    createLabel: function createLabel(e) {
      var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : {};
      var i = De.get(e, this.config);
      return Z("span", _objectSpread(_objectSpread({}, t), {}, {
        class: [t.class, this.config.classNames.hidden].filter(Boolean).join(" ")
      }), i);
    },
    createBadge: function createBadge(e) {
      if (W(e)) return null;
      var t = Z("span", {
        class: this.config.classNames.menu.value
      });
      return t.appendChild(Z("span", {
        class: this.config.classNames.menu.badge
      }, e)), t;
    },
    createButton: function createButton(e, t) {
      var _this6 = this;

      var i = X({}, t);
      var s = Oe(e);
      var n = {
        element: "button",
        toggle: !1,
        label: null,
        icon: null,
        labelPressed: null,
        iconPressed: null
      };

      switch (["element", "icon", "label"].forEach(function (e) {
        Object.keys(i).includes(e) && (n[e] = i[e], delete i[e]);
      }), "button" !== n.element || Object.keys(i).includes("type") || (i.type = "button"), Object.keys(i).includes("class") ? i.class.split(" ").some(function (e) {
        return e === _this6.config.classNames.control;
      }) || X(i, {
        class: "".concat(i.class, " ").concat(this.config.classNames.control)
      }) : i.class = this.config.classNames.control, e) {
        case "play":
          n.toggle = !0, n.label = "play", n.labelPressed = "pause", n.icon = "play", n.iconPressed = "pause";
          break;

        case "mute":
          n.toggle = !0, n.label = "mute", n.labelPressed = "unmute", n.icon = "volume", n.iconPressed = "muted";
          break;

        case "captions":
          n.toggle = !0, n.label = "enableCaptions", n.labelPressed = "disableCaptions", n.icon = "captions-off", n.iconPressed = "captions-on";
          break;

        case "fullscreen":
          n.toggle = !0, n.label = "enterFullscreen", n.labelPressed = "exitFullscreen", n.icon = "enter-fullscreen", n.iconPressed = "exit-fullscreen";
          break;

        case "play-large":
          i.class += " ".concat(this.config.classNames.control, "--overlaid"), s = "play", n.label = "play", n.icon = "play";
          break;

        default:
          W(n.label) && (n.label = s), W(n.icon) && (n.icon = e);
      }

      var a = Z(n.element);
      return n.toggle ? (a.appendChild(Ue.createIcon.call(this, n.iconPressed, {
        class: "icon--pressed"
      })), a.appendChild(Ue.createIcon.call(this, n.icon, {
        class: "icon--not-pressed"
      })), a.appendChild(Ue.createLabel.call(this, n.labelPressed, {
        class: "label--pressed"
      })), a.appendChild(Ue.createLabel.call(this, n.label, {
        class: "label--not-pressed"
      }))) : (a.appendChild(Ue.createIcon.call(this, n.icon)), a.appendChild(Ue.createLabel.call(this, n.label))), X(i, ne(this.config.selectors.buttons[s], i)), G(a, i), "play" === s ? (j(this.elements.buttons[s]) || (this.elements.buttons[s] = []), this.elements.buttons[s].push(a)) : this.elements.buttons[s] = a, a;
    },
    createRange: function createRange(e, t) {
      var i = Z("input", X(ne(this.config.selectors.inputs[e]), {
        type: "range",
        min: 0,
        max: 100,
        step: .01,
        value: 0,
        autocomplete: "off",
        role: "slider",
        "aria-label": De.get(e, this.config),
        "aria-valuemin": 0,
        "aria-valuemax": 100,
        "aria-valuenow": 0
      }, t));
      return this.elements.inputs[e] = i, Ue.updateRangeFill.call(this, i), T.setup(i), i;
    },
    createProgress: function createProgress(e, t) {
      var i = Z("progress", X(ne(this.config.selectors.display[e]), {
        min: 0,
        max: 100,
        value: 0,
        role: "progressbar",
        "aria-hidden": !0
      }, t));

      if ("volume" !== e) {
        i.appendChild(Z("span", null, "0"));

        var _t4 = {
          played: "played",
          buffer: "buffered"
        }[e],
            _s5 = _t4 ? De.get(_t4, this.config) : "";

        i.innerText = "% ".concat(_s5.toLowerCase());
      }

      return this.elements.display[e] = i, i;
    },
    createTime: function createTime(e, t) {
      var i = ne(this.config.selectors.display[e], t),
          s = Z("div", X(i, {
        class: "".concat(i.class ? i.class : "", " ").concat(this.config.classNames.display.time, " ").trim(),
        "aria-label": De.get(e, this.config)
      }), "00:00");
      return this.elements.display[e] = s, s;
    },
    bindMenuItemShortcuts: function bindMenuItemShortcuts(e, t) {
      var _this7 = this;

      fe.call(this, e, "keydown keyup", function (i) {
        if (![32, 38, 39, 40].includes(i.which)) return;
        if (i.preventDefault(), i.stopPropagation(), "keydown" === i.type) return;
        var s = re(e, '[role="menuitemradio"]');
        if (!s && [32, 39].includes(i.which)) Ue.showMenuPanel.call(_this7, t, !0);else {
          var _t5;

          32 !== i.which && (40 === i.which || s && 39 === i.which ? (_t5 = e.nextElementSibling, H(_t5) || (_t5 = e.parentNode.firstElementChild)) : (_t5 = e.previousElementSibling, H(_t5) || (_t5 = e.parentNode.lastElementChild)), ue.call(_this7, _t5, !0));
        }
      }, !1), fe.call(this, e, "keyup", function (e) {
        13 === e.which && Ue.focusFirstMenuItem.call(_this7, null, !0);
      });
    },
    createMenuItem: function createMenuItem(_ref9) {
      var _this8 = this;

      var e = _ref9.value,
          t = _ref9.list,
          i = _ref9.type,
          s = _ref9.title,
          _ref9$badge = _ref9.badge,
          n = _ref9$badge === void 0 ? null : _ref9$badge,
          _ref9$checked = _ref9.checked,
          a = _ref9$checked === void 0 ? !1 : _ref9$checked;
      var l = ne(this.config.selectors.inputs[i]),
          o = Z("button", X(l, {
        type: "button",
        role: "menuitemradio",
        class: "".concat(this.config.classNames.control, " ").concat(l.class ? l.class : "").trim(),
        "aria-checked": a,
        value: e
      })),
          r = Z("span");
      r.innerHTML = s, H(n) && r.appendChild(n), o.appendChild(r), Object.defineProperty(o, "checked", {
        enumerable: !0,
        get: function get() {
          return "true" === o.getAttribute("aria-checked");
        },
        set: function set(e) {
          e && Array.from(o.parentNode.children).filter(function (e) {
            return re(e, '[role="menuitemradio"]');
          }).forEach(function (e) {
            return e.setAttribute("aria-checked", "false");
          }), o.setAttribute("aria-checked", e ? "true" : "false");
        }
      }), this.listeners.bind(o, "click keyup", function (t) {
        if (!R(t) || 32 === t.which) {
          switch (t.preventDefault(), t.stopPropagation(), o.checked = !0, i) {
            case "language":
              _this8.currentTrack = Number(e);
              break;

            case "quality":
              _this8.quality = e;
              break;

            case "speed":
              _this8.speed = parseFloat(e);
          }

          Ue.showMenuPanel.call(_this8, "home", R(t));
        }
      }, i, !1), Ue.bindMenuItemShortcuts.call(this, o, i), t.appendChild(o);
    },
    formatTime: function formatTime() {
      var e = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : 0;
      var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : !1;
      if (!$(e)) return e;
      return Be(e, Ve(this.duration) > 0, t);
    },
    updateTimeDisplay: function updateTimeDisplay() {
      var e = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : null;
      var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : 0;
      var i = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : !1;
      H(e) && $(t) && (e.innerText = Ue.formatTime(t, i));
    },
    updateVolume: function updateVolume() {
      this.supported.ui && (H(this.elements.inputs.volume) && Ue.setRange.call(this, this.elements.inputs.volume, this.muted ? 0 : this.volume), H(this.elements.buttons.mute) && (this.elements.buttons.mute.pressed = this.muted || 0 === this.volume));
    },
    setRange: function setRange(e) {
      var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : 0;
      H(e) && (e.value = t, Ue.updateRangeFill.call(this, e));
    },
    updateProgress: function updateProgress(e) {
      var _this9 = this;

      if (!this.supported.ui || !F(e)) return;
      var t = 0;

      var i = function i(e, t) {
        var i = $(t) ? t : 0,
            s = H(e) ? e : _this9.elements.display.buffer;

        if (H(s)) {
          s.value = i;
          var _e7 = s.getElementsByTagName("span")[0];
          H(_e7) && (_e7.childNodes[0].nodeValue = i);
        }
      };

      if (e) switch (e.type) {
        case "timeupdate":
        case "seeking":
        case "seeked":
          s = this.currentTime, n = this.duration, t = 0 === s || 0 === n || Number.isNaN(s) || Number.isNaN(n) ? 0 : (s / n * 100).toFixed(2), "timeupdate" === e.type && Ue.setRange.call(this, this.elements.inputs.seek, t);
          break;

        case "playing":
        case "progress":
          i(this.elements.display.buffer, 100 * this.buffered);
      }
      var s, n;
    },
    updateRangeFill: function updateRangeFill(e) {
      var t = F(e) ? e.target : e;

      if (H(t) && "range" === t.getAttribute("type")) {
        if (re(t, this.config.selectors.inputs.seek)) {
          t.setAttribute("aria-valuenow", this.currentTime);

          var _e8 = Ue.formatTime(this.currentTime),
              _i5 = Ue.formatTime(this.duration),
              _s6 = De.get("seekLabel", this.config);

          t.setAttribute("aria-valuetext", _s6.replace("{currentTime}", _e8).replace("{duration}", _i5));
        } else if (re(t, this.config.selectors.inputs.volume)) {
          var _e9 = 100 * t.value;

          t.setAttribute("aria-valuenow", _e9), t.setAttribute("aria-valuetext", "".concat(_e9.toFixed(1), "%"));
        } else t.setAttribute("aria-valuenow", t.value);

        Y.isWebkit && t.style.setProperty("--value", t.value / t.max * 100 + "%");
      }
    },
    updateSeekTooltip: function updateSeekTooltip(e) {
      var _this10 = this;

      if (!this.config.tooltips.seek || !H(this.elements.inputs.seek) || !H(this.elements.display.seekTooltip) || 0 === this.duration) return;

      var t = "".concat(this.config.classNames.tooltip, "--visible"),
          i = function i(e) {
        return le(_this10.elements.display.seekTooltip, t, e);
      };

      if (this.touch) return void i(!1);
      var s = 0;
      var n = this.elements.progress.getBoundingClientRect();
      if (F(e)) s = 100 / n.width * (e.pageX - n.left);else {
        if (!oe(this.elements.display.seekTooltip, t)) return;
        s = parseFloat(this.elements.display.seekTooltip.style.left, 10);
      }
      s < 0 ? s = 0 : s > 100 && (s = 100), Ue.updateTimeDisplay.call(this, this.elements.display.seekTooltip, this.duration / 100 * s), this.elements.display.seekTooltip.style.left = "".concat(s, "%"), F(e) && ["mouseenter", "mouseleave"].includes(e.type) && i("mouseenter" === e.type);
    },
    timeUpdate: function timeUpdate(e) {
      var t = !H(this.elements.display.duration) && this.config.invertTime;
      Ue.updateTimeDisplay.call(this, this.elements.display.currentTime, t ? this.duration - this.currentTime : this.currentTime, t), e && "timeupdate" === e.type && this.media.seeking || Ue.updateProgress.call(this, e);
    },
    durationUpdate: function durationUpdate() {
      if (!this.supported.ui || !this.config.invertTime && this.currentTime) return;
      if (this.duration >= Math.pow(2, 32)) return ae(this.elements.display.currentTime, !0), void ae(this.elements.progress, !0);
      H(this.elements.inputs.seek) && this.elements.inputs.seek.setAttribute("aria-valuemax", this.duration);
      var e = H(this.elements.display.duration);
      !e && this.config.displayDuration && this.paused && Ue.updateTimeDisplay.call(this, this.elements.display.currentTime, this.duration), e && Ue.updateTimeDisplay.call(this, this.elements.display.duration, this.duration), Ue.updateSeekTooltip.call(this);
    },
    toggleMenuButton: function toggleMenuButton(e, t) {
      ae(this.elements.settings.buttons[e], !t);
    },
    updateSetting: function updateSetting(e, t, i) {
      var s = this.elements.settings.panels[e];
      var n = null,
          a = t;
      if ("captions" === e) n = this.currentTrack;else {
        if (n = W(i) ? this[e] : i, W(n) && (n = this.config[e].default), !W(this.options[e]) && !this.options[e].includes(n)) return void this.debug.warn("Unsupported value of '".concat(n, "' for ").concat(e));
        if (!this.config[e].options.includes(n)) return void this.debug.warn("Disabled value of '".concat(n, "' for ").concat(e));
      }
      if (H(a) || (a = s && s.querySelector('[role="menu"]')), !H(a)) return;
      this.elements.settings.buttons[e].querySelector(".".concat(this.config.classNames.menu.value)).innerHTML = Ue.getLabel.call(this, e, n);
      var l = a && a.querySelector("[value=\"".concat(n, "\"]"));
      H(l) && (l.checked = !0);
    },
    getLabel: function getLabel(e, t) {
      switch (e) {
        case "speed":
          return 1 === t ? De.get("normal", this.config) : "".concat(t, "&times;");

        case "quality":
          if ($(t)) {
            var _e10 = De.get("qualityLabel.".concat(t), this.config);

            return _e10.length ? _e10 : "".concat(t, "p");
          }

          return _e(t);

        case "captions":
          return Ke.getLabel.call(this);

        default:
          return null;
      }
    },
    setQualityMenu: function setQualityMenu(e) {
      var _this11 = this;

      if (!H(this.elements.settings.panels.quality)) return;
      var t = "quality",
          i = this.elements.settings.panels.quality.querySelector('[role="menu"]');
      j(e) && (this.options.quality = Ce(e).filter(function (e) {
        return _this11.config.quality.options.includes(e);
      }));
      var s = !W(this.options.quality) && this.options.quality.length > 1;
      if (Ue.toggleMenuButton.call(this, t, s), ie(i), Ue.checkMenu.call(this), !s) return;

      var n = function n(e) {
        var t = De.get("qualityBadge.".concat(e), _this11.config);
        return t.length ? Ue.createBadge.call(_this11, t) : null;
      };

      this.options.quality.sort(function (e, t) {
        var i = _this11.config.quality.options;
        return i.indexOf(e) > i.indexOf(t) ? 1 : -1;
      }).forEach(function (e) {
        Ue.createMenuItem.call(_this11, {
          value: e,
          list: i,
          type: t,
          title: Ue.getLabel.call(_this11, "quality", e),
          badge: n(e)
        });
      }), Ue.updateSetting.call(this, t, i);
    },
    setCaptionsMenu: function setCaptionsMenu() {
      var _this12 = this;

      if (!H(this.elements.settings.panels.captions)) return;
      var e = "captions",
          t = this.elements.settings.panels.captions.querySelector('[role="menu"]'),
          i = Ke.getTracks.call(this),
          s = Boolean(i.length);
      if (Ue.toggleMenuButton.call(this, e, s), ie(t), Ue.checkMenu.call(this), !s) return;
      var n = i.map(function (e, i) {
        return {
          value: i,
          checked: _this12.captions.toggled && _this12.currentTrack === i,
          title: Ke.getLabel.call(_this12, e),
          badge: e.language && Ue.createBadge.call(_this12, e.language.toUpperCase()),
          list: t,
          type: "language"
        };
      });
      n.unshift({
        value: -1,
        checked: !this.captions.toggled,
        title: De.get("disabled", this.config),
        list: t,
        type: "language"
      }), n.forEach(Ue.createMenuItem.bind(this)), Ue.updateSetting.call(this, e, t);
    },
    setSpeedMenu: function setSpeedMenu() {
      var _this13 = this;

      if (!H(this.elements.settings.panels.speed)) return;
      var e = "speed",
          t = this.elements.settings.panels.speed.querySelector('[role="menu"]');
      this.options.speed = this.options.speed.filter(function (e) {
        return e >= _this13.minimumSpeed && e <= _this13.maximumSpeed;
      });
      var i = !W(this.options.speed) && this.options.speed.length > 1;
      Ue.toggleMenuButton.call(this, e, i), ie(t), Ue.checkMenu.call(this), i && (this.options.speed.forEach(function (i) {
        Ue.createMenuItem.call(_this13, {
          value: i,
          list: t,
          type: e,
          title: Ue.getLabel.call(_this13, "speed", i)
        });
      }), Ue.updateSetting.call(this, e, t));
    },
    checkMenu: function checkMenu() {
      var e = this.elements.settings.buttons,
          t = !W(e) && Object.values(e).some(function (e) {
        return !e.hidden;
      });
      ae(this.elements.settings.menu, !t);
    },
    focusFirstMenuItem: function focusFirstMenuItem(e) {
      var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : !1;
      if (this.elements.settings.popup.hidden) return;
      var i = e;
      H(i) || (i = Object.values(this.elements.settings.panels).find(function (e) {
        return !e.hidden;
      }));
      var s = i.querySelector('[role^="menuitem"]');
      ue.call(this, s, t);
    },
    toggleMenu: function toggleMenu(e) {
      var t = this.elements.settings.popup,
          i = this.elements.buttons.settings;
      if (!H(t) || !H(i)) return;
      var s = t.hidden;
      var n = s;
      if (O(e)) n = e;else if (R(e) && 27 === e.which) n = !1;else if (F(e)) {
        var _s7 = q(e.composedPath) ? e.composedPath()[0] : e.target,
            _a3 = t.contains(_s7);

        if (_a3 || !_a3 && e.target !== i && n) return;
      }
      i.setAttribute("aria-expanded", n), ae(t, !n), le(this.elements.container, this.config.classNames.menu.open, n), n && R(e) ? Ue.focusFirstMenuItem.call(this, null, !0) : n || s || ue.call(this, i, R(e));
    },
    getMenuSize: function getMenuSize(e) {
      var t = e.cloneNode(!0);
      t.style.position = "absolute", t.style.opacity = 0, t.removeAttribute("hidden"), e.parentNode.appendChild(t);
      var i = t.scrollWidth,
          s = t.scrollHeight;
      return te(t), {
        width: i,
        height: s
      };
    },
    showMenuPanel: function showMenuPanel() {
      var _this14 = this;

      var e = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : "";
      var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : !1;
      var i = this.elements.container.querySelector("#plyr-settings-".concat(this.id, "-").concat(e));
      if (!H(i)) return;
      var s = i.parentNode,
          n = Array.from(s.children).find(function (e) {
        return !e.hidden;
      });

      if (me.transitions && !me.reducedMotion) {
        s.style.width = "".concat(n.scrollWidth, "px"), s.style.height = "".concat(n.scrollHeight, "px");

        var _e11 = Ue.getMenuSize.call(this, i),
            _t6 = function _t6(e) {
          e.target === s && ["width", "height"].includes(e.propertyName) && (s.style.width = "", s.style.height = "", be.call(_this14, s, z, _t6));
        };

        fe.call(this, s, z, _t6), s.style.width = "".concat(_e11.width, "px"), s.style.height = "".concat(_e11.height, "px");
      }

      ae(n, !0), ae(i, !1), Ue.focusFirstMenuItem.call(this, i, t);
    },
    setDownloadUrl: function setDownloadUrl() {
      var e = this.elements.buttons.download;
      H(e) && e.setAttribute("href", this.download);
    },
    create: function create(e) {
      var _this15 = this;

      var t = Ue.bindMenuItemShortcuts,
          i = Ue.createButton,
          s = Ue.createProgress,
          n = Ue.createRange,
          a = Ue.createTime,
          l = Ue.setQualityMenu,
          o = Ue.setSpeedMenu,
          r = Ue.showMenuPanel;
      this.elements.controls = null, j(this.config.controls) && this.config.controls.includes("play-large") && this.elements.container.appendChild(i.call(this, "play-large"));
      var c = Z("div", ne(this.config.selectors.controls.wrapper));
      this.elements.controls = c;
      var h = {
        class: "plyr__controls__item"
      };
      return Ce(j(this.config.controls) ? this.config.controls : []).forEach(function (l) {
        if ("restart" === l && c.appendChild(i.call(_this15, "restart", h)), "rewind" === l && c.appendChild(i.call(_this15, "rewind", h)), "play" === l && c.appendChild(i.call(_this15, "play", h)), "fast-forward" === l && c.appendChild(i.call(_this15, "fast-forward", h)), "progress" === l) {
          var _t7 = Z("div", {
            class: "".concat(h.class, " plyr__progress__container")
          }),
              _i6 = Z("div", ne(_this15.config.selectors.progress));

          if (_i6.appendChild(n.call(_this15, "seek", {
            id: "plyr-seek-".concat(e.id)
          })), _i6.appendChild(s.call(_this15, "buffer")), _this15.config.tooltips.seek) {
            var _e12 = Z("span", {
              class: _this15.config.classNames.tooltip
            }, "00:00");

            _i6.appendChild(_e12), _this15.elements.display.seekTooltip = _e12;
          }

          _this15.elements.progress = _i6, _t7.appendChild(_this15.elements.progress), c.appendChild(_t7);
        }

        if ("current-time" === l && c.appendChild(a.call(_this15, "currentTime", h)), "duration" === l && c.appendChild(a.call(_this15, "duration", h)), "mute" === l || "volume" === l) {
          var _t8 = _this15.elements.volume;

          if (H(_t8) && c.contains(_t8) || (_t8 = Z("div", X({}, h, {
            class: "".concat(h.class, " plyr__volume").trim()
          })), _this15.elements.volume = _t8, c.appendChild(_t8)), "mute" === l && _t8.appendChild(i.call(_this15, "mute")), "volume" === l && !Y.isIos) {
            var _i7 = {
              max: 1,
              step: .05,
              value: _this15.config.volume
            };

            _t8.appendChild(n.call(_this15, "volume", X(_i7, {
              id: "plyr-volume-".concat(e.id)
            })));
          }
        }

        if ("captions" === l && c.appendChild(i.call(_this15, "captions", h)), "settings" === l && !W(_this15.config.settings)) {
          var _s8 = Z("div", X({}, h, {
            class: "".concat(h.class, " plyr__menu").trim(),
            hidden: ""
          }));

          _s8.appendChild(i.call(_this15, "settings", {
            "aria-haspopup": !0,
            "aria-controls": "plyr-settings-".concat(e.id),
            "aria-expanded": !1
          }));

          var _n4 = Z("div", {
            class: "plyr__menu__container",
            id: "plyr-settings-".concat(e.id),
            hidden: ""
          }),
              _a4 = Z("div"),
              _l3 = Z("div", {
            id: "plyr-settings-".concat(e.id, "-home")
          }),
              _o2 = Z("div", {
            role: "menu"
          });

          _l3.appendChild(_o2), _a4.appendChild(_l3), _this15.elements.settings.panels.home = _l3, _this15.config.settings.forEach(function (i) {
            var s = Z("button", X(ne(_this15.config.selectors.buttons.settings), {
              type: "button",
              class: "".concat(_this15.config.classNames.control, " ").concat(_this15.config.classNames.control, "--forward"),
              role: "menuitem",
              "aria-haspopup": !0,
              hidden: ""
            }));
            t.call(_this15, s, i), fe.call(_this15, s, "click", function () {
              r.call(_this15, i, !1);
            });
            var n = Z("span", null, De.get(i, _this15.config)),
                l = Z("span", {
              class: _this15.config.classNames.menu.value
            });
            l.innerHTML = e[i], n.appendChild(l), s.appendChild(n), _o2.appendChild(s);
            var c = Z("div", {
              id: "plyr-settings-".concat(e.id, "-").concat(i),
              hidden: ""
            }),
                h = Z("button", {
              type: "button",
              class: "".concat(_this15.config.classNames.control, " ").concat(_this15.config.classNames.control, "--back")
            });
            h.appendChild(Z("span", {
              "aria-hidden": !0
            }, De.get(i, _this15.config))), h.appendChild(Z("span", {
              class: _this15.config.classNames.hidden
            }, De.get("menuBack", _this15.config))), fe.call(_this15, c, "keydown", function (e) {
              37 === e.which && (e.preventDefault(), e.stopPropagation(), r.call(_this15, "home", !0));
            }, !1), fe.call(_this15, h, "click", function () {
              r.call(_this15, "home", !1);
            }), c.appendChild(h), c.appendChild(Z("div", {
              role: "menu"
            })), _a4.appendChild(c), _this15.elements.settings.buttons[i] = s, _this15.elements.settings.panels[i] = c;
          }), _n4.appendChild(_a4), _s8.appendChild(_n4), c.appendChild(_s8), _this15.elements.settings.popup = _n4, _this15.elements.settings.menu = _s8;
        }

        if ("pip" === l && me.pip && c.appendChild(i.call(_this15, "pip", h)), "airplay" === l && me.airplay && c.appendChild(i.call(_this15, "airplay", h)), "download" === l) {
          var _e13 = X({}, h, {
            element: "a",
            href: _this15.download,
            target: "_blank"
          });

          _this15.isHTML5 && (_e13.download = "");
          var _t9 = _this15.config.urls.download;
          !U(_t9) && _this15.isEmbed && X(_e13, {
            icon: "logo-".concat(_this15.provider),
            label: _this15.provider
          }), c.appendChild(i.call(_this15, "download", _e13));
        }

        "fullscreen" === l && c.appendChild(i.call(_this15, "fullscreen", h));
      }), this.isHTML5 && l.call(this, Ie.getQualityOptions.call(this)), o.call(this), c;
    },
    inject: function inject() {
      var _this16 = this;

      if (this.config.loadSprite) {
        var _e14 = Ue.getIconUrl.call(this);

        _e14.cors && Re(_e14.url, "sprite-plyr");
      }

      this.id = Math.floor(1e4 * Math.random());
      var e = null;
      this.elements.controls = null;
      var t = {
        id: this.id,
        seektime: this.config.seekTime,
        title: this.config.title
      };
      var i = !0;
      q(this.config.controls) && (this.config.controls = this.config.controls.call(this, t)), this.config.controls || (this.config.controls = []), H(this.config.controls) || _(this.config.controls) ? e = this.config.controls : (e = Ue.create.call(this, {
        id: this.id,
        seektime: this.config.seekTime,
        speed: this.speed,
        quality: this.quality,
        captions: Ke.getLabel.call(this)
      }), i = !1);
      var s;
      i && _(this.config.controls) && (e = function (e) {
        var i = e;
        return Object.entries(t).forEach(function (_ref10) {
          var _ref11 = _slicedToArray(_ref10, 2),
              e = _ref11[0],
              t = _ref11[1];

          i = $e(i, "{".concat(e, "}"), t);
        }), i;
      }(e)), _(this.config.selectors.controls.container) && (s = document.querySelector(this.config.selectors.controls.container)), H(s) || (s = this.elements.container);

      if (s[H(e) ? "insertAdjacentElement" : "insertAdjacentHTML"]("afterbegin", e), H(this.elements.controls) || Ue.findElements.call(this), !W(this.elements.buttons)) {
        var _e15 = function _e15(e) {
          var t = _this16.config.classNames.controlPressed;
          Object.defineProperty(e, "pressed", {
            enumerable: !0,
            get: function get() {
              return oe(e, t);
            },
            set: function set() {
              var i = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : !1;
              le(e, t, i);
            }
          });
        };

        Object.values(this.elements.buttons).filter(Boolean).forEach(function (t) {
          j(t) || D(t) ? Array.from(t).filter(Boolean).forEach(_e15) : _e15(t);
        });
      }

      if (Y.isEdge && K(s), this.config.tooltips.controls) {
        var _this$config = this.config,
            _e16 = _this$config.classNames,
            _t10 = _this$config.selectors,
            _i8 = "".concat(_t10.controls.wrapper, " ").concat(_t10.labels, " .").concat(_e16.hidden),
            _s9 = ce.call(this, _i8);

        Array.from(_s9).forEach(function (e) {
          le(e, _this16.config.classNames.hidden, !1), le(e, _this16.config.classNames.tooltip, !0);
        });
      }
    }
  };

  function We(e) {
    var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : !0;
    var i = e;

    if (t) {
      var _e17 = document.createElement("a");

      _e17.href = i, i = _e17.href;
    }

    try {
      return new URL(i);
    } catch (e) {
      return null;
    }
  }

  function ze(e) {
    var t = new URLSearchParams();
    return L(e) && Object.entries(e).forEach(function (_ref12) {
      var _ref13 = _slicedToArray(_ref12, 2),
          e = _ref13[0],
          i = _ref13[1];

      t.set(e, i);
    }), t;
  }

  var Ke = {
    setup: function setup() {
      var _i9, _i10, _this$config$captions;

      if (!this.supported.ui) return;
      if (!this.isVideo || this.isYouTube || this.isHTML5 && !me.textTracks) return void (j(this.config.controls) && this.config.controls.includes("settings") && this.config.settings.includes("captions") && Ue.setCaptionsMenu.call(this));
      var e, t;

      if (H(this.elements.captions) || (this.elements.captions = Z("div", ne(this.config.selectors.captions)), e = this.elements.captions, t = this.elements.wrapper, H(e) && H(t) && t.parentNode.insertBefore(e, t.nextSibling)), Y.isIE && window.URL) {
        var _e18 = this.media.querySelectorAll("track");

        Array.from(_e18).forEach(function (e) {
          var t = e.getAttribute("src"),
              i = We(t);
          null !== i && i.hostname !== window.location.href.hostname && ["http:", "https:"].includes(i.protocol) && Fe(t, "blob").then(function (t) {
            e.setAttribute("src", window.URL.createObjectURL(t));
          }).catch(function () {
            te(e);
          });
        });
      }

      var i = Ce((navigator.languages || [navigator.language || navigator.userLanguage || "en"]).map(function (e) {
        return e.split("-")[0];
      }));
      var s = (this.storage.get("language") || this.config.captions.language || "auto").toLowerCase();
      "auto" === s && (_i9 = i, _i10 = _slicedToArray(_i9, 1), s = _i10[0], _i9);
      var n = this.storage.get("captions");

      if (O(n) || (_this$config$captions = this.config.captions, n = _this$config$captions.active, _this$config$captions), Object.assign(this.captions, {
        toggled: !1,
        active: n,
        language: s,
        languages: i
      }), this.isHTML5) {
        var _e19 = this.config.captions.update ? "addtrack removetrack" : "removetrack";

        fe.call(this, this.media.textTracks, _e19, Ke.update.bind(this));
      }

      setTimeout(Ke.update.bind(this), 0);
    },
    update: function update() {
      var _this17 = this;

      var e = Ke.getTracks.call(this, !0),
          _this$captions = this.captions,
          t = _this$captions.active,
          i = _this$captions.language,
          s = _this$captions.meta,
          n = _this$captions.currentTrackNode,
          a = Boolean(e.find(function (e) {
        return e.language === i;
      }));
      this.isHTML5 && this.isVideo && e.filter(function (e) {
        return !s.get(e);
      }).forEach(function (e) {
        _this17.debug.log("Track added", e), s.set(e, {
          default: "showing" === e.mode
        }), "showing" === e.mode && (e.mode = "hidden"), fe.call(_this17, e, "cuechange", function () {
          return Ke.updateCues.call(_this17);
        });
      }), (a && this.language !== i || !e.includes(n)) && (Ke.setLanguage.call(this, i), Ke.toggle.call(this, t && a)), le(this.elements.container, this.config.classNames.captions.enabled, !W(e)), j(this.config.controls) && this.config.controls.includes("settings") && this.config.settings.includes("captions") && Ue.setCaptionsMenu.call(this);
    },
    toggle: function toggle(e) {
      var _this18 = this;

      var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : !0;
      if (!this.supported.ui) return;
      var i = this.captions.toggled,
          s = this.config.classNames.captions.active,
          n = I(e) ? !i : e;

      if (n !== i) {
        if (t || (this.captions.active = n, this.storage.set({
          captions: n
        })), !this.language && n && !t) {
          var _e20 = Ke.getTracks.call(this),
              _t11 = Ke.findTrack.call(this, [this.captions.language].concat(_toConsumableArray(this.captions.languages)), !0);

          return this.captions.language = _t11.language, void Ke.set.call(this, _e20.indexOf(_t11));
        }

        this.elements.buttons.captions && (this.elements.buttons.captions.pressed = n), le(this.elements.container, s, n), this.captions.toggled = n, Ue.updateSetting.call(this, "captions"), ve.call(this, this.media, n ? "captionsenabled" : "captionsdisabled");
      }

      setTimeout(function () {
        n && _this18.captions.toggled && (_this18.captions.currentTrackNode.mode = "hidden");
      });
    },
    set: function set(e) {
      var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : !0;
      var i = Ke.getTracks.call(this);
      if (-1 !== e) {
        if ($(e)) {
          if (e in i) {
            if (this.captions.currentTrack !== e) {
              this.captions.currentTrack = e;

              var _s10 = i[e],
                  _ref14 = _s10 || {},
                  _n5 = _ref14.language;

              this.captions.currentTrackNode = _s10, Ue.updateSetting.call(this, "captions"), t || (this.captions.language = _n5, this.storage.set({
                language: _n5
              })), this.isVimeo && this.embed.enableTextTrack(_n5), ve.call(this, this.media, "languagechange");
            }

            Ke.toggle.call(this, !0, t), this.isHTML5 && this.isVideo && Ke.updateCues.call(this);
          } else this.debug.warn("Track not found", e);
        } else this.debug.warn("Invalid caption argument", e);
      } else Ke.toggle.call(this, !1, t);
    },
    setLanguage: function setLanguage(e) {
      var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : !0;
      if (!_(e)) return void this.debug.warn("Invalid language argument", e);
      var i = e.toLowerCase();
      this.captions.language = i;
      var s = Ke.getTracks.call(this),
          n = Ke.findTrack.call(this, [i]);
      Ke.set.call(this, s.indexOf(n), t);
    },
    getTracks: function getTracks() {
      var _this19 = this;

      var e = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : !1;
      return Array.from((this.media || {}).textTracks || []).filter(function (t) {
        return !_this19.isHTML5 || e || _this19.captions.meta.has(t);
      }).filter(function (e) {
        return ["captions", "subtitles"].includes(e.kind);
      });
    },
    findTrack: function findTrack(e) {
      var _this20 = this;

      var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : !1;

      var i = Ke.getTracks.call(this),
          s = function s(e) {
        return Number((_this20.captions.meta.get(e) || {}).default);
      },
          n = Array.from(i).sort(function (e, t) {
        return s(t) - s(e);
      });

      var a;
      return e.every(function (e) {
        return a = n.find(function (t) {
          return t.language === e;
        }), !a;
      }), a || (t ? n[0] : void 0);
    },
    getCurrentTrack: function getCurrentTrack() {
      return Ke.getTracks.call(this)[this.currentTrack];
    },
    getLabel: function getLabel(e) {
      var t = e;
      return !V(t) && me.textTracks && this.captions.toggled && (t = Ke.getCurrentTrack.call(this)), V(t) ? W(t.label) ? W(t.language) ? De.get("enabled", this.config) : e.language.toUpperCase() : t.label : De.get("disabled", this.config);
    },
    updateCues: function updateCues(e) {
      if (!this.supported.ui) return;
      if (!H(this.elements.captions)) return void this.debug.warn("No captions element to render to");
      if (!I(e) && !Array.isArray(e)) return void this.debug.warn("updateCues: Invalid input", e);
      var t = e;

      if (!t) {
        var _e21 = Ke.getCurrentTrack.call(this);

        t = Array.from((_e21 || {}).activeCues || []).map(function (e) {
          return e.getCueAsHTML();
        }).map(qe);
      }

      var i = t.map(function (e) {
        return e.trim();
      }).join("\n");

      if (i !== this.elements.captions.innerHTML) {
        ie(this.elements.captions);

        var _e22 = Z("span", ne(this.config.selectors.caption));

        _e22.innerHTML = i, this.elements.captions.appendChild(_e22), ve.call(this, this.media, "cuechange");
      }
    }
  },
      Ye = {
    enabled: !0,
    title: "",
    debug: !1,
    autoplay: !1,
    autopause: !0,
    playsinline: !0,
    seekTime: 10,
    volume: 1,
    muted: !1,
    duration: null,
    displayDuration: !0,
    invertTime: !0,
    toggleInvert: !0,
    ratio: null,
    clickToPlay: !0,
    hideControls: !0,
    resetOnEnd: !1,
    disableContextMenu: !0,
    loadSprite: !0,
    iconPrefix: "plyr",
    iconUrl: "https://cdn.plyr.io/3.6.7/plyr.svg",
    blankVideo: "https://cdn.plyr.io/static/blank.mp4",
    quality: {
      default: 576,
      options: [4320, 2880, 2160, 1440, 1080, 720, 576, 480, 360, 240],
      forced: !1,
      onChange: null
    },
    loop: {
      active: !1
    },
    speed: {
      selected: 1,
      options: [.5, .75, 1, 1.25, 1.5, 1.75, 2, 4]
    },
    keyboard: {
      focused: !0,
      global: !1
    },
    tooltips: {
      controls: !1,
      seek: !0
    },
    captions: {
      active: !1,
      language: "auto",
      update: !1
    },
    fullscreen: {
      enabled: !0,
      fallback: !0,
      iosNative: !1
    },
    storage: {
      enabled: !0,
      key: "plyr"
    },
    controls: ["play-large", "play", "progress", "current-time", "mute", "volume", "captions", "settings", "pip", "airplay", "fullscreen"],
    settings: ["captions", "quality", "speed"],
    i18n: {
      restart: "Restart",
      rewind: "Rewind {seektime}s",
      play: "Play",
      pause: "Pause",
      fastForward: "Forward {seektime}s",
      seek: "Seek",
      seekLabel: "{currentTime} of {duration}",
      played: "Played",
      buffered: "Buffered",
      currentTime: "Current time",
      duration: "Duration",
      volume: "Volume",
      mute: "Mute",
      unmute: "Unmute",
      enableCaptions: "Enable captions",
      disableCaptions: "Disable captions",
      download: "Download",
      enterFullscreen: "Enter fullscreen",
      exitFullscreen: "Exit fullscreen",
      frameTitle: "Player for {title}",
      captions: "Captions",
      settings: "Settings",
      pip: "PIP",
      menuBack: "Go back to previous menu",
      speed: "Speed",
      normal: "Normal",
      quality: "Quality",
      loop: "Loop",
      start: "Start",
      end: "End",
      all: "All",
      reset: "Reset",
      disabled: "Disabled",
      enabled: "Enabled",
      advertisement: "Ad",
      qualityBadge: {
        2160: "4K",
        1440: "HD",
        1080: "HD",
        720: "HD",
        576: "SD",
        480: "SD"
      }
    },
    urls: {
      download: null,
      vimeo: {
        sdk: "https://player.vimeo.com/api/player.js",
        iframe: "https://player.vimeo.com/video/{0}?{1}",
        api: "https://vimeo.com/api/oembed.json?url={0}"
      },
      youtube: {
        sdk: "https://www.youtube.com/iframe_api",
        api: "https://noembed.com/embed?url=https://www.youtube.com/watch?v={0}"
      },
      googleIMA: {
        sdk: "https://imasdk.googleapis.com/js/sdkloader/ima3.js"
      }
    },
    listeners: {
      seek: null,
      play: null,
      pause: null,
      restart: null,
      rewind: null,
      fastForward: null,
      mute: null,
      volume: null,
      captions: null,
      download: null,
      fullscreen: null,
      pip: null,
      airplay: null,
      speed: null,
      quality: null,
      loop: null,
      language: null
    },
    events: ["ended", "progress", "stalled", "playing", "waiting", "canplay", "canplaythrough", "loadstart", "loadeddata", "loadedmetadata", "timeupdate", "volumechange", "play", "pause", "error", "seeking", "seeked", "emptied", "ratechange", "cuechange", "download", "enterfullscreen", "exitfullscreen", "captionsenabled", "captionsdisabled", "languagechange", "controlshidden", "controlsshown", "ready", "statechange", "qualitychange", "adsloaded", "adscontentpause", "adscontentresume", "adstarted", "adsmidpoint", "adscomplete", "adsallcomplete", "adsimpression", "adsclick"],
    selectors: {
      editable: "input, textarea, select, [contenteditable]",
      container: ".plyr",
      controls: {
        container: null,
        wrapper: ".plyr__controls"
      },
      labels: "[data-plyr]",
      buttons: {
        play: '[data-plyr="play"]',
        pause: '[data-plyr="pause"]',
        restart: '[data-plyr="restart"]',
        rewind: '[data-plyr="rewind"]',
        fastForward: '[data-plyr="fast-forward"]',
        mute: '[data-plyr="mute"]',
        captions: '[data-plyr="captions"]',
        download: '[data-plyr="download"]',
        fullscreen: '[data-plyr="fullscreen"]',
        pip: '[data-plyr="pip"]',
        airplay: '[data-plyr="airplay"]',
        settings: '[data-plyr="settings"]',
        loop: '[data-plyr="loop"]'
      },
      inputs: {
        seek: '[data-plyr="seek"]',
        volume: '[data-plyr="volume"]',
        speed: '[data-plyr="speed"]',
        language: '[data-plyr="language"]',
        quality: '[data-plyr="quality"]'
      },
      display: {
        currentTime: ".plyr__time--current",
        duration: ".plyr__time--duration",
        buffer: ".plyr__progress__buffer",
        loop: ".plyr__progress__loop",
        volume: ".plyr__volume--display"
      },
      progress: ".plyr__progress",
      captions: ".plyr__captions",
      caption: ".plyr__caption"
    },
    classNames: {
      type: "plyr--{0}",
      provider: "plyr--{0}",
      video: "plyr__video-wrapper",
      embed: "plyr__video-embed",
      videoFixedRatio: "plyr__video-wrapper--fixed-ratio",
      embedContainer: "plyr__video-embed__container",
      poster: "plyr__poster",
      posterEnabled: "plyr__poster-enabled",
      ads: "plyr__ads",
      control: "plyr__control",
      controlPressed: "plyr__control--pressed",
      playing: "plyr--playing",
      paused: "plyr--paused",
      stopped: "plyr--stopped",
      loading: "plyr--loading",
      hover: "plyr--hover",
      tooltip: "plyr__tooltip",
      cues: "plyr__cues",
      hidden: "plyr__sr-only",
      hideControls: "plyr--hide-controls",
      isIos: "plyr--is-ios",
      isTouch: "plyr--is-touch",
      uiSupported: "plyr--full-ui",
      noTransition: "plyr--no-transition",
      display: {
        time: "plyr__time"
      },
      menu: {
        value: "plyr__menu__value",
        badge: "plyr__badge",
        open: "plyr--menu-open"
      },
      captions: {
        enabled: "plyr--captions-enabled",
        active: "plyr--captions-active"
      },
      fullscreen: {
        enabled: "plyr--fullscreen-enabled",
        fallback: "plyr--fullscreen-fallback"
      },
      pip: {
        supported: "plyr--pip-supported",
        active: "plyr--pip-active"
      },
      airplay: {
        supported: "plyr--airplay-supported",
        active: "plyr--airplay-active"
      },
      tabFocus: "plyr__tab-focus",
      previewThumbnails: {
        thumbContainer: "plyr__preview-thumb",
        thumbContainerShown: "plyr__preview-thumb--is-shown",
        imageContainer: "plyr__preview-thumb__image-container",
        timeContainer: "plyr__preview-thumb__time-container",
        scrubbingContainer: "plyr__preview-scrubbing",
        scrubbingContainerShown: "plyr__preview-scrubbing--is-shown"
      }
    },
    attributes: {
      embed: {
        provider: "data-plyr-provider",
        id: "data-plyr-embed-id"
      }
    },
    ads: {
      enabled: !1,
      publisherId: "",
      tagUrl: ""
    },
    previewThumbnails: {
      enabled: !1,
      src: ""
    },
    vimeo: {
      byline: !1,
      portrait: !1,
      title: !1,
      speed: !0,
      transparent: !1,
      customControls: !0,
      referrerPolicy: null,
      premium: !1
    },
    youtube: {
      rel: 0,
      showinfo: 0,
      iv_load_policy: 3,
      modestbranding: 1,
      customControls: !0,
      noCookie: !1
    }
  },
      Qe = "picture-in-picture",
      Xe = "inline",
      Je = {
    html5: "html5",
    youtube: "youtube",
    vimeo: "vimeo"
  },
      Ge = "audio",
      Ze = "video";

  var et = function et() {};

  var tt = /*#__PURE__*/function () {
    function tt() {
      var e = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : !1;

      _classCallCheck(this, tt);

      this.enabled = window.console && e, this.enabled && this.log("Debugging enabled");
    }

    _createClass(tt, [{
      key: "log",
      get: function get() {
        return this.enabled ? Function.prototype.bind.call(console.log, console) : et;
      }
    }, {
      key: "warn",
      get: function get() {
        return this.enabled ? Function.prototype.bind.call(console.warn, console) : et;
      }
    }, {
      key: "error",
      get: function get() {
        return this.enabled ? Function.prototype.bind.call(console.error, console) : et;
      }
    }]);

    return tt;
  }();

  var it = /*#__PURE__*/function () {
    function it(t) {
      var _this21 = this;

      _classCallCheck(this, it);

      e(this, "onChange", function () {
        if (!_this21.enabled) return;
        var e = _this21.player.elements.buttons.fullscreen;
        H(e) && (e.pressed = _this21.active);
        var t = _this21.target === _this21.player.media ? _this21.target : _this21.player.elements.container;
        ve.call(_this21.player, t, _this21.active ? "enterfullscreen" : "exitfullscreen", !0);
      }), e(this, "toggleFallback", function () {
        var e = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : !1;

        if (e ? _this21.scrollPosition = {
          x: window.scrollX || 0,
          y: window.scrollY || 0
        } : window.scrollTo(_this21.scrollPosition.x, _this21.scrollPosition.y), document.body.style.overflow = e ? "hidden" : "", le(_this21.target, _this21.player.config.classNames.fullscreen.fallback, e), Y.isIos) {
          var _t12 = document.head.querySelector('meta[name="viewport"]');

          var _i11 = "viewport-fit=cover";
          _t12 || (_t12 = document.createElement("meta"), _t12.setAttribute("name", "viewport"));

          var _s11 = _(_t12.content) && _t12.content.includes(_i11);

          e ? (_this21.cleanupViewport = !_s11, _s11 || (_t12.content += ",".concat(_i11))) : _this21.cleanupViewport && (_t12.content = _t12.content.split(",").filter(function (e) {
            return e.trim() !== _i11;
          }).join(","));
        }

        _this21.onChange();
      }), e(this, "trapFocus", function (e) {
        if (Y.isIos || !_this21.active || "Tab" !== e.key || 9 !== e.keyCode) return;

        var t = document.activeElement,
            i = ce.call(_this21.player, "a[href], button:not(:disabled), input:not(:disabled), [tabindex]"),
            _i12 = _slicedToArray(i, 1),
            s = _i12[0],
            n = i[i.length - 1];

        t !== n || e.shiftKey ? t === s && e.shiftKey && (n.focus(), e.preventDefault()) : (s.focus(), e.preventDefault());
      }), e(this, "update", function () {
        if (_this21.enabled) {
          var _e23;

          _e23 = _this21.forceFallback ? "Fallback (forced)" : it.native ? "Native" : "Fallback", _this21.player.debug.log("".concat(_e23, " fullscreen enabled"));
        } else _this21.player.debug.log("Fullscreen not supported and fallback disabled");

        le(_this21.player.elements.container, _this21.player.config.classNames.fullscreen.enabled, _this21.enabled);
      }), e(this, "enter", function () {
        _this21.enabled && (Y.isIos && _this21.player.config.fullscreen.iosNative ? _this21.player.isVimeo ? _this21.player.embed.requestFullscreen() : _this21.target.webkitEnterFullscreen() : !it.native || _this21.forceFallback ? _this21.toggleFallback(!0) : _this21.prefix ? W(_this21.prefix) || _this21.target["".concat(_this21.prefix, "Request").concat(_this21.property)]() : _this21.target.requestFullscreen({
          navigationUI: "hide"
        }));
      }), e(this, "exit", function () {
        if (_this21.enabled) if (Y.isIos && _this21.player.config.fullscreen.iosNative) _this21.target.webkitExitFullscreen(), ke(_this21.player.play());else if (!it.native || _this21.forceFallback) _this21.toggleFallback(!1);else if (_this21.prefix) {
          if (!W(_this21.prefix)) {
            var _e24 = "moz" === _this21.prefix ? "Cancel" : "Exit";

            document["".concat(_this21.prefix).concat(_e24).concat(_this21.property)]();
          }
        } else (document.cancelFullScreen || document.exitFullscreen).call(document);
      }), e(this, "toggle", function () {
        _this21.active ? _this21.exit() : _this21.enter();
      }), this.player = t, this.prefix = it.prefix, this.property = it.property, this.scrollPosition = {
        x: 0,
        y: 0
      }, this.forceFallback = "force" === t.config.fullscreen.fallback, this.player.elements.fullscreen = t.config.fullscreen.container && function (e, t) {
        var _Element2 = Element,
            i = _Element2.prototype;
        return (i.closest || function () {
          var e = this;

          do {
            if (re.matches(e, t)) return e;
            e = e.parentElement || e.parentNode;
          } while (null !== e && 1 === e.nodeType);

          return null;
        }).call(e, t);
      }(this.player.elements.container, t.config.fullscreen.container), fe.call(this.player, document, "ms" === this.prefix ? "MSFullscreenChange" : "".concat(this.prefix, "fullscreenchange"), function () {
        _this21.onChange();
      }), fe.call(this.player, this.player.elements.container, "dblclick", function (e) {
        H(_this21.player.elements.controls) && _this21.player.elements.controls.contains(e.target) || _this21.player.listeners.proxy(e, _this21.toggle, "fullscreen");
      }), fe.call(this, this.player.elements.container, "keydown", function (e) {
        return _this21.trapFocus(e);
      }), this.update();
    }

    _createClass(it, [{
      key: "usingNative",
      get: function get() {
        return it.native && !this.forceFallback;
      }
    }, {
      key: "enabled",
      get: function get() {
        return (it.native || this.player.config.fullscreen.fallback) && this.player.config.fullscreen.enabled && this.player.supported.ui && this.player.isVideo;
      }
    }, {
      key: "active",
      get: function get() {
        if (!this.enabled) return !1;
        if (!it.native || this.forceFallback) return oe(this.target, this.player.config.classNames.fullscreen.fallback);
        var e = this.prefix ? document["".concat(this.prefix).concat(this.property, "Element")] : document.fullscreenElement;
        return e && e.shadowRoot ? e === this.target.getRootNode().host : e === this.target;
      }
    }, {
      key: "target",
      get: function get() {
        return Y.isIos && this.player.config.fullscreen.iosNative ? this.player.media : this.player.elements.fullscreen || this.player.elements.container;
      }
    }], [{
      key: "native",
      get: function get() {
        return !!(document.fullscreenEnabled || document.webkitFullscreenEnabled || document.mozFullScreenEnabled || document.msFullscreenEnabled);
      }
    }, {
      key: "prefix",
      get: function get() {
        if (q(document.exitFullscreen)) return "";
        var e = "";
        return ["webkit", "moz", "ms"].some(function (t) {
          return !(!q(document["".concat(t, "ExitFullscreen")]) && !q(document["".concat(t, "CancelFullScreen")])) && (e = t, !0);
        }), e;
      }
    }, {
      key: "property",
      get: function get() {
        return "moz" === this.prefix ? "FullScreen" : "Fullscreen";
      }
    }]);

    return it;
  }();

  function st(e) {
    var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : 1;
    return new Promise(function (i, s) {
      var n = new Image(),
          a = function a() {
        delete n.onload, delete n.onerror, (n.naturalWidth >= t ? i : s)(n);
      };

      Object.assign(n, {
        onload: a,
        onerror: a,
        src: e
      });
    });
  }

  var nt = {
    addStyleHook: function addStyleHook() {
      le(this.elements.container, this.config.selectors.container.replace(".", ""), !0), le(this.elements.container, this.config.classNames.uiSupported, this.supported.ui);
    },
    toggleNativeControls: function toggleNativeControls() {
      var e = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : !1;
      e && this.isHTML5 ? this.media.setAttribute("controls", "") : this.media.removeAttribute("controls");
    },
    build: function build() {
      var _this22 = this;

      if (this.listeners.media(), !this.supported.ui) return this.debug.warn("Basic support only for ".concat(this.provider, " ").concat(this.type)), void nt.toggleNativeControls.call(this, !0);
      H(this.elements.controls) || (Ue.inject.call(this), this.listeners.controls()), nt.toggleNativeControls.call(this), this.isHTML5 && Ke.setup.call(this), this.volume = null, this.muted = null, this.loop = null, this.quality = null, this.speed = null, Ue.updateVolume.call(this), Ue.timeUpdate.call(this), nt.checkPlaying.call(this), le(this.elements.container, this.config.classNames.pip.supported, me.pip && this.isHTML5 && this.isVideo), le(this.elements.container, this.config.classNames.airplay.supported, me.airplay && this.isHTML5), le(this.elements.container, this.config.classNames.isIos, Y.isIos), le(this.elements.container, this.config.classNames.isTouch, this.touch), this.ready = !0, setTimeout(function () {
        ve.call(_this22, _this22.media, "ready");
      }, 0), nt.setTitle.call(this), this.poster && nt.setPoster.call(this, this.poster, !1).catch(function () {}), this.config.duration && Ue.durationUpdate.call(this);
    },
    setTitle: function setTitle() {
      var e = De.get("play", this.config);

      if (_(this.config.title) && !W(this.config.title) && (e += ", ".concat(this.config.title)), Array.from(this.elements.buttons.play || []).forEach(function (t) {
        t.setAttribute("aria-label", e);
      }), this.isEmbed) {
        var _e25 = he.call(this, "iframe");

        if (!H(_e25)) return;

        var _t13 = W(this.config.title) ? "video" : this.config.title,
            _i13 = De.get("frameTitle", this.config);

        _e25.setAttribute("title", _i13.replace("{title}", _t13));
      }
    },
    togglePoster: function togglePoster(e) {
      le(this.elements.container, this.config.classNames.posterEnabled, e);
    },
    setPoster: function setPoster(e) {
      var _this23 = this;

      var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : !0;
      return t && this.poster ? Promise.reject(new Error("Poster already set")) : (this.media.setAttribute("data-poster", e), this.elements.poster.removeAttribute("hidden"), Te.call(this).then(function () {
        return st(e);
      }).catch(function (t) {
        throw e === _this23.poster && nt.togglePoster.call(_this23, !1), t;
      }).then(function () {
        if (e !== _this23.poster) throw new Error("setPoster cancelled by later call to setPoster");
      }).then(function () {
        return Object.assign(_this23.elements.poster.style, {
          backgroundImage: "url('".concat(e, "')"),
          backgroundSize: ""
        }), nt.togglePoster.call(_this23, !0), e;
      }));
    },
    checkPlaying: function checkPlaying(e) {
      var _this24 = this;

      le(this.elements.container, this.config.classNames.playing, this.playing), le(this.elements.container, this.config.classNames.paused, this.paused), le(this.elements.container, this.config.classNames.stopped, this.stopped), Array.from(this.elements.buttons.play || []).forEach(function (e) {
        Object.assign(e, {
          pressed: _this24.playing
        }), e.setAttribute("aria-label", De.get(_this24.playing ? "pause" : "play", _this24.config));
      }), F(e) && "timeupdate" === e.type || nt.toggleControls.call(this);
    },
    checkLoading: function checkLoading(e) {
      var _this25 = this;

      this.loading = ["stalled", "waiting"].includes(e.type), clearTimeout(this.timers.loading), this.timers.loading = setTimeout(function () {
        le(_this25.elements.container, _this25.config.classNames.loading, _this25.loading), nt.toggleControls.call(_this25);
      }, this.loading ? 250 : 0);
    },
    toggleControls: function toggleControls(e) {
      var t = this.elements.controls;

      if (t && this.config.hideControls) {
        var _i14 = this.touch && this.lastSeekTime + 2e3 > Date.now();

        this.toggleControls(Boolean(e || this.loading || this.paused || t.pressed || t.hover || _i14));
      }
    },
    migrateStyles: function migrateStyles() {
      var _this26 = this;

      Object.values(_objectSpread({}, this.media.style)).filter(function (e) {
        return !W(e) && _(e) && e.startsWith("--plyr");
      }).forEach(function (e) {
        _this26.elements.container.style.setProperty(e, _this26.media.style.getPropertyValue(e)), _this26.media.style.removeProperty(e);
      }), W(this.media.style) && this.media.removeAttribute("style");
    }
  };

  var at = /*#__PURE__*/function () {
    function at(t) {
      var _this27 = this;

      _classCallCheck(this, at);

      e(this, "firstTouch", function () {
        var e = _this27.player,
            t = e.elements;
        e.touch = !0, le(t.container, e.config.classNames.isTouch, !0);
      }), e(this, "setTabFocus", function (e) {
        var t = _this27.player,
            i = t.elements;
        if (clearTimeout(_this27.focusTimer), "keydown" === e.type && 9 !== e.which) return;
        "keydown" === e.type && (_this27.lastKeyDown = e.timeStamp);
        var s = e.timeStamp - _this27.lastKeyDown <= 20;
        ("focus" !== e.type || s) && (function () {
          var e = t.config.classNames.tabFocus;
          le(ce.call(t, ".".concat(e)), e, !1);
        }(), "focusout" !== e.type && (_this27.focusTimer = setTimeout(function () {
          var e = document.activeElement;
          i.container.contains(e) && le(document.activeElement, t.config.classNames.tabFocus, !0);
        }, 10)));
      }), e(this, "global", function () {
        var e = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : !0;
        var t = _this27.player;
        t.config.keyboard.global && ge.call(t, window, "keydown keyup", _this27.handleKey, e, !1), ge.call(t, document.body, "click", _this27.toggleMenu, e), ye.call(t, document.body, "touchstart", _this27.firstTouch), ge.call(t, document.body, "keydown focus blur focusout", _this27.setTabFocus, e, !1, !0);
      }), e(this, "container", function () {
        var e = _this27.player,
            t = e.config,
            i = e.elements,
            s = e.timers;
        !t.keyboard.global && t.keyboard.focused && fe.call(e, i.container, "keydown keyup", _this27.handleKey, !1), fe.call(e, i.container, "mousemove mouseleave touchstart touchmove enterfullscreen exitfullscreen", function (t) {
          var n = i.controls;
          n && "enterfullscreen" === t.type && (n.pressed = !1, n.hover = !1);
          var a = 0;
          ["touchstart", "touchmove", "mousemove"].includes(t.type) && (nt.toggleControls.call(e, !0), a = e.touch ? 3e3 : 2e3), clearTimeout(s.controls), s.controls = setTimeout(function () {
            return nt.toggleControls.call(e, !1);
          }, a);
        });

        var n = function n(t) {
          if (!t) return Me.call(e);
          var s = i.container.getBoundingClientRect(),
              n = s.width,
              a = s.height;
          return Me.call(e, "".concat(n, ":").concat(a));
        },
            a = function a() {
          clearTimeout(s.resized), s.resized = setTimeout(n, 50);
        };

        fe.call(e, i.container, "enterfullscreen exitfullscreen", function (t) {
          var _e$fullscreen = e.fullscreen,
              s = _e$fullscreen.target,
              l = _e$fullscreen.usingNative;
          if (s !== i.container) return;
          if (!e.isEmbed && W(e.config.ratio)) return;

          var o = "enterfullscreen" === t.type,
              _n6 = n(o),
              r = _n6.padding,
              c = _n6.ratio;

          (function (t, i, s) {
            if (!e.isVimeo || e.config.vimeo.premium) return;

            var n = e.elements.wrapper.firstChild,
                _t14 = _slicedToArray(t, 2),
                a = _t14[1],
                _Ne$call = Ne.call(e),
                _Ne$call2 = _slicedToArray(_Ne$call, 2),
                l = _Ne$call2[0],
                o = _Ne$call2[1];

            n.style.maxWidth = s ? a / o * l + "px" : null, n.style.margin = s ? "0 auto" : null;
          })(c, 0, o), o && setTimeout(function () {
            return K(i.container);
          }, 100), l || (o ? fe.call(e, window, "resize", a) : be.call(e, window, "resize", a));
        });
      }), e(this, "media", function () {
        var e = _this27.player,
            t = e.elements;

        if (fe.call(e, e.media, "timeupdate seeking seeked", function (t) {
          return Ue.timeUpdate.call(e, t);
        }), fe.call(e, e.media, "durationchange loadeddata loadedmetadata", function (t) {
          return Ue.durationUpdate.call(e, t);
        }), fe.call(e, e.media, "ended", function () {
          e.isHTML5 && e.isVideo && e.config.resetOnEnd && (e.restart(), e.pause());
        }), fe.call(e, e.media, "progress playing seeking seeked", function (t) {
          return Ue.updateProgress.call(e, t);
        }), fe.call(e, e.media, "volumechange", function (t) {
          return Ue.updateVolume.call(e, t);
        }), fe.call(e, e.media, "playing play pause ended emptied timeupdate", function (t) {
          return nt.checkPlaying.call(e, t);
        }), fe.call(e, e.media, "waiting canplay seeked playing", function (t) {
          return nt.checkLoading.call(e, t);
        }), e.supported.ui && e.config.clickToPlay && !e.isAudio) {
          var _i15 = he.call(e, ".".concat(e.config.classNames.video));

          if (!H(_i15)) return;
          fe.call(e, t.container, "click", function (s) {
            ([t.container, _i15].includes(s.target) || _i15.contains(s.target)) && (e.touch && e.config.hideControls || (e.ended ? (_this27.proxy(s, e.restart, "restart"), _this27.proxy(s, function () {
              ke(e.play());
            }, "play")) : _this27.proxy(s, function () {
              ke(e.togglePlay());
            }, "play")));
          });
        }

        e.supported.ui && e.config.disableContextMenu && fe.call(e, t.wrapper, "contextmenu", function (e) {
          e.preventDefault();
        }, !1), fe.call(e, e.media, "volumechange", function () {
          e.storage.set({
            volume: e.volume,
            muted: e.muted
          });
        }), fe.call(e, e.media, "ratechange", function () {
          Ue.updateSetting.call(e, "speed"), e.storage.set({
            speed: e.speed
          });
        }), fe.call(e, e.media, "qualitychange", function (t) {
          Ue.updateSetting.call(e, "quality", null, t.detail.quality);
        }), fe.call(e, e.media, "ready qualitychange", function () {
          Ue.setDownloadUrl.call(e);
        });
        var i = e.config.events.concat(["keyup", "keydown"]).join(" ");
        fe.call(e, e.media, i, function (i) {
          var _i$detail = i.detail,
              s = _i$detail === void 0 ? {} : _i$detail;
          "error" === i.type && (s = e.media.error), ve.call(e, t.container, i.type, !0, s);
        });
      }), e(this, "proxy", function (e, t, i) {
        var s = _this27.player,
            n = s.config.listeners[i];
        var a = !0;
        q(n) && (a = n.call(s, e)), !1 !== a && q(t) && t.call(s, e);
      }), e(this, "bind", function (e, t, i, s) {
        var n = arguments.length > 4 && arguments[4] !== undefined ? arguments[4] : !0;
        var a = _this27.player,
            l = a.config.listeners[s],
            o = q(l);
        fe.call(a, e, t, function (e) {
          return _this27.proxy(e, i, s);
        }, n && !o);
      }), e(this, "controls", function () {
        var e = _this27.player,
            t = e.elements,
            i = Y.isIE ? "change" : "input";

        if (t.buttons.play && Array.from(t.buttons.play).forEach(function (t) {
          _this27.bind(t, "click", function () {
            ke(e.togglePlay());
          }, "play");
        }), _this27.bind(t.buttons.restart, "click", e.restart, "restart"), _this27.bind(t.buttons.rewind, "click", function () {
          e.lastSeekTime = Date.now(), e.rewind();
        }, "rewind"), _this27.bind(t.buttons.fastForward, "click", function () {
          e.lastSeekTime = Date.now(), e.forward();
        }, "fastForward"), _this27.bind(t.buttons.mute, "click", function () {
          e.muted = !e.muted;
        }, "mute"), _this27.bind(t.buttons.captions, "click", function () {
          return e.toggleCaptions();
        }), _this27.bind(t.buttons.download, "click", function () {
          ve.call(e, e.media, "download");
        }, "download"), _this27.bind(t.buttons.fullscreen, "click", function () {
          e.fullscreen.toggle();
        }, "fullscreen"), _this27.bind(t.buttons.pip, "click", function () {
          e.pip = "toggle";
        }, "pip"), _this27.bind(t.buttons.airplay, "click", e.airplay, "airplay"), _this27.bind(t.buttons.settings, "click", function (t) {
          t.stopPropagation(), t.preventDefault(), Ue.toggleMenu.call(e, t);
        }, null, !1), _this27.bind(t.buttons.settings, "keyup", function (t) {
          var i = t.which;
          [13, 32].includes(i) && (13 !== i ? (t.preventDefault(), t.stopPropagation(), Ue.toggleMenu.call(e, t)) : Ue.focusFirstMenuItem.call(e, null, !0));
        }, null, !1), _this27.bind(t.settings.menu, "keydown", function (t) {
          27 === t.which && Ue.toggleMenu.call(e, t);
        }), _this27.bind(t.inputs.seek, "mousedown mousemove", function (e) {
          var i = t.progress.getBoundingClientRect(),
              s = 100 / i.width * (e.pageX - i.left);
          e.currentTarget.setAttribute("seek-value", s);
        }), _this27.bind(t.inputs.seek, "mousedown mouseup keydown keyup touchstart touchend", function (t) {
          var i = t.currentTarget,
              s = t.keyCode ? t.keyCode : t.which,
              n = "play-on-seeked";
          if (R(t) && 39 !== s && 37 !== s) return;
          e.lastSeekTime = Date.now();
          var a = i.hasAttribute(n),
              l = ["mouseup", "touchend", "keyup"].includes(t.type);
          a && l ? (i.removeAttribute(n), ke(e.play())) : !l && e.playing && (i.setAttribute(n, ""), e.pause());
        }), Y.isIos) {
          var _t15 = ce.call(e, 'input[type="range"]');

          Array.from(_t15).forEach(function (e) {
            return _this27.bind(e, i, function (e) {
              return K(e.target);
            });
          });
        }

        _this27.bind(t.inputs.seek, i, function (t) {
          var i = t.currentTarget;
          var s = i.getAttribute("seek-value");
          W(s) && (s = i.value), i.removeAttribute("seek-value"), e.currentTime = s / i.max * e.duration;
        }, "seek"), _this27.bind(t.progress, "mouseenter mouseleave mousemove", function (t) {
          return Ue.updateSeekTooltip.call(e, t);
        }), _this27.bind(t.progress, "mousemove touchmove", function (t) {
          var i = e.previewThumbnails;
          i && i.loaded && i.startMove(t);
        }), _this27.bind(t.progress, "mouseleave touchend click", function () {
          var t = e.previewThumbnails;
          t && t.loaded && t.endMove(!1, !0);
        }), _this27.bind(t.progress, "mousedown touchstart", function (t) {
          var i = e.previewThumbnails;
          i && i.loaded && i.startScrubbing(t);
        }), _this27.bind(t.progress, "mouseup touchend", function (t) {
          var i = e.previewThumbnails;
          i && i.loaded && i.endScrubbing(t);
        }), Y.isWebkit && Array.from(ce.call(e, 'input[type="range"]')).forEach(function (t) {
          _this27.bind(t, "input", function (t) {
            return Ue.updateRangeFill.call(e, t.target);
          });
        }), e.config.toggleInvert && !H(t.display.duration) && _this27.bind(t.display.currentTime, "click", function () {
          0 !== e.currentTime && (e.config.invertTime = !e.config.invertTime, Ue.timeUpdate.call(e));
        }), _this27.bind(t.inputs.volume, i, function (t) {
          e.volume = t.target.value;
        }, "volume"), _this27.bind(t.controls, "mouseenter mouseleave", function (i) {
          t.controls.hover = !e.touch && "mouseenter" === i.type;
        }), t.fullscreen && Array.from(t.fullscreen.children).filter(function (e) {
          return !e.contains(t.container);
        }).forEach(function (i) {
          _this27.bind(i, "mouseenter mouseleave", function (i) {
            t.controls.hover = !e.touch && "mouseenter" === i.type;
          });
        }), _this27.bind(t.controls, "mousedown mouseup touchstart touchend touchcancel", function (e) {
          t.controls.pressed = ["mousedown", "touchstart"].includes(e.type);
        }), _this27.bind(t.controls, "focusin", function () {
          var i = e.config,
              s = e.timers;
          le(t.controls, i.classNames.noTransition, !0), nt.toggleControls.call(e, !0), setTimeout(function () {
            le(t.controls, i.classNames.noTransition, !1);
          }, 0);
          var n = _this27.touch ? 3e3 : 4e3;
          clearTimeout(s.controls), s.controls = setTimeout(function () {
            return nt.toggleControls.call(e, !1);
          }, n);
        }), _this27.bind(t.inputs.volume, "wheel", function (t) {
          var i = t.webkitDirectionInvertedFromDevice,
              _map = [t.deltaX, -t.deltaY].map(function (e) {
            return i ? -e : e;
          }),
              _map2 = _slicedToArray(_map, 2),
              s = _map2[0],
              n = _map2[1],
              a = Math.sign(Math.abs(s) > Math.abs(n) ? s : n);

          e.increaseVolume(a / 50);
          var l = e.media.volume;
          (1 === a && l < 1 || -1 === a && l > 0) && t.preventDefault();
        }, "volume", !1);
      }), this.player = t, this.lastKey = null, this.focusTimer = null, this.lastKeyDown = null, this.handleKey = this.handleKey.bind(this), this.toggleMenu = this.toggleMenu.bind(this), this.setTabFocus = this.setTabFocus.bind(this), this.firstTouch = this.firstTouch.bind(this);
    }

    _createClass(at, [{
      key: "handleKey",
      value: function handleKey(e) {
        var t = this.player,
            i = t.elements,
            s = e.keyCode ? e.keyCode : e.which,
            n = "keydown" === e.type,
            a = n && s === this.lastKey;
        if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
        if (!$(s)) return;

        if (n) {
          var _n7 = document.activeElement;

          if (H(_n7)) {
            var _s12 = t.config.selectors.editable,
                _a5 = i.inputs.seek;
            if (_n7 !== _a5 && re(_n7, _s12)) return;
            if (32 === e.which && re(_n7, 'button, [role^="menuitem"]')) return;
          }

          switch ([32, 37, 38, 39, 40, 48, 49, 50, 51, 52, 53, 54, 56, 57, 67, 70, 73, 75, 76, 77, 79].includes(s) && (e.preventDefault(), e.stopPropagation()), s) {
            case 48:
            case 49:
            case 50:
            case 51:
            case 52:
            case 53:
            case 54:
            case 55:
            case 56:
            case 57:
              a || (t.currentTime = t.duration / 10 * (s - 48));
              break;

            case 32:
            case 75:
              a || ke(t.togglePlay());
              break;

            case 38:
              t.increaseVolume(.1);
              break;

            case 40:
              t.decreaseVolume(.1);
              break;

            case 77:
              a || (t.muted = !t.muted);
              break;

            case 39:
              t.forward();
              break;

            case 37:
              t.rewind();
              break;

            case 70:
              t.fullscreen.toggle();
              break;

            case 67:
              a || t.toggleCaptions();
              break;

            case 76:
              t.loop = !t.loop;
          }

          27 === s && !t.fullscreen.usingNative && t.fullscreen.active && t.fullscreen.toggle(), this.lastKey = s;
        } else this.lastKey = null;
      }
    }, {
      key: "toggleMenu",
      value: function toggleMenu(e) {
        Ue.toggleMenu.call(this.player, e);
      }
    }]);

    return at;
  }();

  "undefined" != typeof globalThis ? globalThis : "undefined" != typeof window ? window : "undefined" != typeof global ? global : "undefined" != typeof self && self;

  var lt = function (e, t) {
    return e(t = {
      exports: {}
    }, t.exports), t.exports;
  }(function (e, t) {
    e.exports = function () {
      var e = function e() {},
          t = {},
          i = {},
          s = {};

      function n(e, t) {
        e = e.push ? e : [e];
        var n,
            a,
            l,
            o = [],
            r = e.length,
            c = r;

        for (n = function n(e, i) {
          i.length && o.push(e), --c || t(o);
        }; r--;) {
          a = e[r], (l = i[a]) ? n(a, l) : (s[a] = s[a] || []).push(n);
        }
      }

      function a(e, t) {
        if (e) {
          var n = s[e];
          if (i[e] = t, n) for (; n.length;) {
            n[0](e, t), n.splice(0, 1);
          }
        }
      }

      function l(t, i) {
        t.call && (t = {
          success: t
        }), i.length ? (t.error || e)(i) : (t.success || e)(t);
      }

      function o(t, i, s, n) {
        var a,
            l,
            r = document,
            c = s.async,
            h = (s.numRetries || 0) + 1,
            u = s.before || e,
            d = t.replace(/[\?|#].*$/, ""),
            m = t.replace(/^(css|img)!/, "");
        n = n || 0, /(^css!|\.css$)/.test(d) ? ((l = r.createElement("link")).rel = "stylesheet", l.href = m, (a = "hideFocus" in l) && l.relList && (a = 0, l.rel = "preload", l.as = "style")) : /(^img!|\.(png|gif|jpg|svg|webp)$)/.test(d) ? (l = r.createElement("img")).src = m : ((l = r.createElement("script")).src = t, l.async = void 0 === c || c), l.onload = l.onerror = l.onbeforeload = function (e) {
          var r = e.type[0];
          if (a) try {
            l.sheet.cssText.length || (r = "e");
          } catch (e) {
            18 != e.code && (r = "e");
          }

          if ("e" == r) {
            if ((n += 1) < h) return o(t, i, s, n);
          } else if ("preload" == l.rel && "style" == l.as) return l.rel = "stylesheet";

          i(t, r, e.defaultPrevented);
        }, !1 !== u(t, l) && r.head.appendChild(l);
      }

      function r(e, t, i) {
        var s,
            n,
            a = (e = e.push ? e : [e]).length,
            l = a,
            r = [];

        for (s = function s(e, i, _s13) {
          if ("e" == i && r.push(e), "b" == i) {
            if (!_s13) return;
            r.push(e);
          }

          --a || t(r);
        }, n = 0; n < l; n++) {
          o(e[n], s, i);
        }
      }

      function c(e, i, s) {
        var n, o;

        if (i && i.trim && (n = i), o = (n ? s : i) || {}, n) {
          if (n in t) throw "LoadJS";
          t[n] = !0;
        }

        function c(t, i) {
          r(e, function (e) {
            l(o, e), t && l({
              success: t,
              error: i
            }, e), a(n, e);
          }, o);
        }

        if (o.returnPromise) return new Promise(c);
        c();
      }

      return c.ready = function (e, t) {
        return n(e, function (e) {
          l(t, e);
        }), c;
      }, c.done = function (e) {
        a(e, []);
      }, c.reset = function () {
        t = {}, i = {}, s = {};
      }, c.isDefined = function (e) {
        return e in t;
      }, c;
    }();
  });

  function ot(e) {
    return new Promise(function (t, i) {
      lt(e, {
        success: t,
        error: i
      });
    });
  }

  function rt(e) {
    e && !this.embed.hasPlayed && (this.embed.hasPlayed = !0), this.media.paused === e && (this.media.paused = !e, ve.call(this, this.media, e ? "play" : "pause"));
  }

  var ct = {
    setup: function setup() {
      var e = this;
      le(e.elements.wrapper, e.config.classNames.embed, !0), e.options.speed = e.config.speed.options, Me.call(e), L(window.Vimeo) ? ct.ready.call(e) : ot(e.config.urls.vimeo.sdk).then(function () {
        ct.ready.call(e);
      }).catch(function (t) {
        e.debug.warn("Vimeo SDK (player.js) failed to load", t);
      });
    },
    ready: function ready() {
      var _this28 = this;

      var e = this,
          t = e.config.vimeo,
          i = t.premium,
          s = t.referrerPolicy,
          n = _objectWithoutProperties(t, ["premium", "referrerPolicy"]);

      i && Object.assign(n, {
        controls: !1,
        sidedock: !1
      });
      var a = ze(_objectSpread({
        loop: e.config.loop.active,
        autoplay: e.autoplay,
        muted: e.muted,
        gesture: "media",
        playsinline: !this.config.fullscreen.iosNative
      }, n));
      var l = e.media.getAttribute("src");
      W(l) && (l = e.media.getAttribute(e.config.attributes.embed.id));
      var o = W(r = l) ? null : $(Number(r)) ? r : r.match(/^.*(vimeo.com\/|video\/)(\d+).*/) ? RegExp.$2 : r;
      var r;
      var c = Z("iframe"),
          h = Le(e.config.urls.vimeo.iframe, o, a);
      if (c.setAttribute("src", h), c.setAttribute("allowfullscreen", ""), c.setAttribute("allow", ["autoplay", "fullscreen", "picture-in-picture", "encrypted-media", "accelerometer", "gyroscope"].join("; ")), W(s) || c.setAttribute("referrerPolicy", s), i || !t.customControls) c.setAttribute("data-poster", e.poster), e.media = se(c, e.media);else {
        var _t16 = Z("div", {
          class: e.config.classNames.embedContainer,
          "data-poster": e.poster
        });

        _t16.appendChild(c), e.media = se(_t16, e.media);
      }
      t.customControls || Fe(Le(e.config.urls.vimeo.api, h)).then(function (t) {
        !W(t) && t.thumbnail_url && nt.setPoster.call(e, t.thumbnail_url).catch(function () {});
      }), e.embed = new window.Vimeo.Player(c, {
        autopause: e.config.autopause,
        muted: e.muted
      }), e.media.paused = !0, e.media.currentTime = 0, e.supported.ui && e.embed.disableTextTrack(), e.media.play = function () {
        return rt.call(e, !0), e.embed.play();
      }, e.media.pause = function () {
        return rt.call(e, !1), e.embed.pause();
      }, e.media.stop = function () {
        e.pause(), e.currentTime = 0;
      };
      var u = e.media.currentTime;
      Object.defineProperty(e.media, "currentTime", {
        get: function get() {
          return u;
        },
        set: function set(t) {
          var i = e.embed,
              s = e.media,
              n = e.paused,
              a = e.volume,
              l = n && !i.hasPlayed;
          s.seeking = !0, ve.call(e, s, "seeking"), Promise.resolve(l && i.setVolume(0)).then(function () {
            return i.setCurrentTime(t);
          }).then(function () {
            return l && i.pause();
          }).then(function () {
            return l && i.setVolume(a);
          }).catch(function () {});
        }
      });
      var d = e.config.speed.selected;
      Object.defineProperty(e.media, "playbackRate", {
        get: function get() {
          return d;
        },
        set: function set(t) {
          e.embed.setPlaybackRate(t).then(function () {
            d = t, ve.call(e, e.media, "ratechange");
          }).catch(function () {
            e.options.speed = [1];
          });
        }
      });
      var m = e.config.volume;
      Object.defineProperty(e.media, "volume", {
        get: function get() {
          return m;
        },
        set: function set(t) {
          e.embed.setVolume(t).then(function () {
            m = t, ve.call(e, e.media, "volumechange");
          });
        }
      });
      var p = e.config.muted;
      Object.defineProperty(e.media, "muted", {
        get: function get() {
          return p;
        },
        set: function set(t) {
          var i = !!O(t) && t;
          e.embed.setVolume(i ? 0 : e.config.volume).then(function () {
            p = i, ve.call(e, e.media, "volumechange");
          });
        }
      });
      var g,
          f = e.config.loop;
      Object.defineProperty(e.media, "loop", {
        get: function get() {
          return f;
        },
        set: function set(t) {
          var i = O(t) ? t : e.config.loop.active;
          e.embed.setLoop(i).then(function () {
            f = i;
          });
        }
      }), e.embed.getVideoUrl().then(function (t) {
        g = t, Ue.setDownloadUrl.call(e);
      }).catch(function (e) {
        _this28.debug.warn(e);
      }), Object.defineProperty(e.media, "currentSrc", {
        get: function get() {
          return g;
        }
      }), Object.defineProperty(e.media, "ended", {
        get: function get() {
          return e.currentTime === e.duration;
        }
      }), Promise.all([e.embed.getVideoWidth(), e.embed.getVideoHeight()]).then(function (t) {
        var _t17 = _slicedToArray(t, 2),
            i = _t17[0],
            s = _t17[1];

        e.embed.ratio = xe(i, s), Me.call(_this28);
      }), e.embed.setAutopause(e.config.autopause).then(function (t) {
        e.config.autopause = t;
      }), e.embed.getVideoTitle().then(function (t) {
        e.config.title = t, nt.setTitle.call(_this28);
      }), e.embed.getCurrentTime().then(function (t) {
        u = t, ve.call(e, e.media, "timeupdate");
      }), e.embed.getDuration().then(function (t) {
        e.media.duration = t, ve.call(e, e.media, "durationchange");
      }), e.embed.getTextTracks().then(function (t) {
        e.media.textTracks = t, Ke.setup.call(e);
      }), e.embed.on("cuechange", function (_ref15) {
        var _ref15$cues = _ref15.cues,
            t = _ref15$cues === void 0 ? [] : _ref15$cues;
        var i = t.map(function (e) {
          return function (e) {
            var t = document.createDocumentFragment(),
                i = document.createElement("div");
            return t.appendChild(i), i.innerHTML = e, t.firstChild.innerText;
          }(e.text);
        });
        Ke.updateCues.call(e, i);
      }), e.embed.on("loaded", function () {
        if (e.embed.getPaused().then(function (t) {
          rt.call(e, !t), t || ve.call(e, e.media, "playing");
        }), H(e.embed.element) && e.supported.ui) {
          e.embed.element.setAttribute("tabindex", -1);
        }
      }), e.embed.on("bufferstart", function () {
        ve.call(e, e.media, "waiting");
      }), e.embed.on("bufferend", function () {
        ve.call(e, e.media, "playing");
      }), e.embed.on("play", function () {
        rt.call(e, !0), ve.call(e, e.media, "playing");
      }), e.embed.on("pause", function () {
        rt.call(e, !1);
      }), e.embed.on("timeupdate", function (t) {
        e.media.seeking = !1, u = t.seconds, ve.call(e, e.media, "timeupdate");
      }), e.embed.on("progress", function (t) {
        e.media.buffered = t.percent, ve.call(e, e.media, "progress"), 1 === parseInt(t.percent, 10) && ve.call(e, e.media, "canplaythrough"), e.embed.getDuration().then(function (t) {
          t !== e.media.duration && (e.media.duration = t, ve.call(e, e.media, "durationchange"));
        });
      }), e.embed.on("seeked", function () {
        e.media.seeking = !1, ve.call(e, e.media, "seeked");
      }), e.embed.on("ended", function () {
        e.media.paused = !0, ve.call(e, e.media, "ended");
      }), e.embed.on("error", function (t) {
        e.media.error = t, ve.call(e, e.media, "error");
      }), t.customControls && setTimeout(function () {
        return nt.build.call(e);
      }, 0);
    }
  };

  function ht(e) {
    e && !this.embed.hasPlayed && (this.embed.hasPlayed = !0), this.media.paused === e && (this.media.paused = !e, ve.call(this, this.media, e ? "play" : "pause"));
  }

  function ut(e) {
    return e.noCookie ? "https://www.youtube-nocookie.com" : "http:" === window.location.protocol ? "http://www.youtube.com" : void 0;
  }

  var dt = {
    setup: function setup() {
      var _this29 = this;

      if (le(this.elements.wrapper, this.config.classNames.embed, !0), L(window.YT) && q(window.YT.Player)) dt.ready.call(this);else {
        var _e26 = window.onYouTubeIframeAPIReady;
        window.onYouTubeIframeAPIReady = function () {
          q(_e26) && _e26(), dt.ready.call(_this29);
        }, ot(this.config.urls.youtube.sdk).catch(function (e) {
          _this29.debug.warn("YouTube API failed to load", e);
        });
      }
    },
    getTitle: function getTitle(e) {
      var _this30 = this;

      Fe(Le(this.config.urls.youtube.api, e)).then(function (e) {
        if (L(e)) {
          var _t18 = e.title,
              _i16 = e.height,
              _s14 = e.width;
          _this30.config.title = _t18, nt.setTitle.call(_this30), _this30.embed.ratio = xe(_s14, _i16);
        }

        Me.call(_this30);
      }).catch(function () {
        Me.call(_this30);
      });
    },
    ready: function ready() {
      var e = this,
          t = e.config.youtube,
          i = e.media && e.media.getAttribute("id");
      if (!W(i) && i.startsWith("youtube-")) return;
      var s = e.media.getAttribute("src");
      W(s) && (s = e.media.getAttribute(this.config.attributes.embed.id));
      var n = W(a = s) ? null : a.match(/^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/) ? RegExp.$2 : a;
      var a;
      var l = Z("div", {
        id: "".concat(e.provider, "-").concat(Math.floor(1e4 * Math.random())),
        "data-poster": t.customControls ? e.poster : void 0
      });

      if (e.media = se(l, e.media), t.customControls) {
        var _t19 = function _t19(e) {
          return "https://i.ytimg.com/vi/".concat(n, "/").concat(e, "default.jpg");
        };

        st(_t19("maxres"), 121).catch(function () {
          return st(_t19("sd"), 121);
        }).catch(function () {
          return st(_t19("hq"));
        }).then(function (t) {
          return nt.setPoster.call(e, t.src);
        }).then(function (t) {
          t.includes("maxres") || (e.elements.poster.style.backgroundSize = "cover");
        }).catch(function () {});
      }

      e.embed = new window.YT.Player(e.media, {
        videoId: n,
        host: ut(t),
        playerVars: X({}, {
          autoplay: e.config.autoplay ? 1 : 0,
          hl: e.config.hl,
          controls: e.supported.ui && t.customControls ? 0 : 1,
          disablekb: 1,
          playsinline: e.config.fullscreen.iosNative ? 0 : 1,
          cc_load_policy: e.captions.active ? 1 : 0,
          cc_lang_pref: e.config.captions.language,
          widget_referrer: window ? window.location.href : null
        }, t),
        events: {
          onError: function onError(t) {
            if (!e.media.error) {
              var _i17 = t.data,
                  _s15 = {
                2: "The request contains an invalid parameter value. For example, this error occurs if you specify a video ID that does not have 11 characters, or if the video ID contains invalid characters, such as exclamation points or asterisks.",
                5: "The requested content cannot be played in an HTML5 player or another error related to the HTML5 player has occurred.",
                100: "The video requested was not found. This error occurs when a video has been removed (for any reason) or has been marked as private.",
                101: "The owner of the requested video does not allow it to be played in embedded players.",
                150: "The owner of the requested video does not allow it to be played in embedded players."
              }[_i17] || "An unknown error occured";

              e.media.error = {
                code: _i17,
                message: _s15
              }, ve.call(e, e.media, "error");
            }
          },
          onPlaybackRateChange: function onPlaybackRateChange(t) {
            var i = t.target;
            e.media.playbackRate = i.getPlaybackRate(), ve.call(e, e.media, "ratechange");
          },
          onReady: function onReady(i) {
            if (q(e.media.play)) return;
            var s = i.target;
            dt.getTitle.call(e, n), e.media.play = function () {
              ht.call(e, !0), s.playVideo();
            }, e.media.pause = function () {
              ht.call(e, !1), s.pauseVideo();
            }, e.media.stop = function () {
              s.stopVideo();
            }, e.media.duration = s.getDuration(), e.media.paused = !0, e.media.currentTime = 0, Object.defineProperty(e.media, "currentTime", {
              get: function get() {
                return Number(s.getCurrentTime());
              },
              set: function set(t) {
                e.paused && !e.embed.hasPlayed && e.embed.mute(), e.media.seeking = !0, ve.call(e, e.media, "seeking"), s.seekTo(t);
              }
            }), Object.defineProperty(e.media, "playbackRate", {
              get: function get() {
                return s.getPlaybackRate();
              },
              set: function set(e) {
                s.setPlaybackRate(e);
              }
            });
            var a = e.config.volume;
            Object.defineProperty(e.media, "volume", {
              get: function get() {
                return a;
              },
              set: function set(t) {
                a = t, s.setVolume(100 * a), ve.call(e, e.media, "volumechange");
              }
            });
            var l = e.config.muted;
            Object.defineProperty(e.media, "muted", {
              get: function get() {
                return l;
              },
              set: function set(t) {
                var i = O(t) ? t : l;
                l = i, s[i ? "mute" : "unMute"](), s.setVolume(100 * a), ve.call(e, e.media, "volumechange");
              }
            }), Object.defineProperty(e.media, "currentSrc", {
              get: function get() {
                return s.getVideoUrl();
              }
            }), Object.defineProperty(e.media, "ended", {
              get: function get() {
                return e.currentTime === e.duration;
              }
            });
            var o = s.getAvailablePlaybackRates();
            e.options.speed = o.filter(function (t) {
              return e.config.speed.options.includes(t);
            }), e.supported.ui && t.customControls && e.media.setAttribute("tabindex", -1), ve.call(e, e.media, "timeupdate"), ve.call(e, e.media, "durationchange"), clearInterval(e.timers.buffering), e.timers.buffering = setInterval(function () {
              e.media.buffered = s.getVideoLoadedFraction(), (null === e.media.lastBuffered || e.media.lastBuffered < e.media.buffered) && ve.call(e, e.media, "progress"), e.media.lastBuffered = e.media.buffered, 1 === e.media.buffered && (clearInterval(e.timers.buffering), ve.call(e, e.media, "canplaythrough"));
            }, 200), t.customControls && setTimeout(function () {
              return nt.build.call(e);
            }, 50);
          },
          onStateChange: function onStateChange(i) {
            var s = i.target;
            clearInterval(e.timers.playing);

            switch (e.media.seeking && [1, 2].includes(i.data) && (e.media.seeking = !1, ve.call(e, e.media, "seeked")), i.data) {
              case -1:
                ve.call(e, e.media, "timeupdate"), e.media.buffered = s.getVideoLoadedFraction(), ve.call(e, e.media, "progress");
                break;

              case 0:
                ht.call(e, !1), e.media.loop ? (s.stopVideo(), s.playVideo()) : ve.call(e, e.media, "ended");
                break;

              case 1:
                t.customControls && !e.config.autoplay && e.media.paused && !e.embed.hasPlayed ? e.media.pause() : (ht.call(e, !0), ve.call(e, e.media, "playing"), e.timers.playing = setInterval(function () {
                  ve.call(e, e.media, "timeupdate");
                }, 50), e.media.duration !== s.getDuration() && (e.media.duration = s.getDuration(), ve.call(e, e.media, "durationchange")));
                break;

              case 2:
                e.muted || e.embed.unMute(), ht.call(e, !1);
                break;

              case 3:
                ve.call(e, e.media, "waiting");
            }

            ve.call(e, e.elements.container, "statechange", !1, {
              code: i.data
            });
          }
        }
      });
    }
  },
      mt = {
    setup: function setup() {
      this.media ? (le(this.elements.container, this.config.classNames.type.replace("{0}", this.type), !0), le(this.elements.container, this.config.classNames.provider.replace("{0}", this.provider), !0), this.isEmbed && le(this.elements.container, this.config.classNames.type.replace("{0}", "video"), !0), this.isVideo && (this.elements.wrapper = Z("div", {
        class: this.config.classNames.video
      }), J(this.media, this.elements.wrapper), this.elements.poster = Z("div", {
        class: this.config.classNames.poster
      }), this.elements.wrapper.appendChild(this.elements.poster)), this.isHTML5 ? Ie.setup.call(this) : this.isYouTube ? dt.setup.call(this) : this.isVimeo && ct.setup.call(this)) : this.debug.warn("No media element found!");
    }
  };

  var pt = /*#__PURE__*/function () {
    function pt(t) {
      var _this31 = this;

      _classCallCheck(this, pt);

      e(this, "load", function () {
        _this31.enabled && (L(window.google) && L(window.google.ima) ? _this31.ready() : ot(_this31.player.config.urls.googleIMA.sdk).then(function () {
          _this31.ready();
        }).catch(function () {
          _this31.trigger("error", new Error("Google IMA SDK failed to load"));
        }));
      }), e(this, "ready", function () {
        var e;
        _this31.enabled || ((e = _this31).manager && e.manager.destroy(), e.elements.displayContainer && e.elements.displayContainer.destroy(), e.elements.container.remove()), _this31.startSafetyTimer(12e3, "ready()"), _this31.managerPromise.then(function () {
          _this31.clearSafetyTimer("onAdsManagerLoaded()");
        }), _this31.listeners(), _this31.setupIMA();
      }), e(this, "setupIMA", function () {
        _this31.elements.container = Z("div", {
          class: _this31.player.config.classNames.ads
        }), _this31.player.elements.container.appendChild(_this31.elements.container), google.ima.settings.setVpaidMode(google.ima.ImaSdkSettings.VpaidMode.ENABLED), google.ima.settings.setLocale(_this31.player.config.ads.language), google.ima.settings.setDisableCustomPlaybackForIOS10Plus(_this31.player.config.playsinline), _this31.elements.displayContainer = new google.ima.AdDisplayContainer(_this31.elements.container, _this31.player.media), _this31.loader = new google.ima.AdsLoader(_this31.elements.displayContainer), _this31.loader.addEventListener(google.ima.AdsManagerLoadedEvent.Type.ADS_MANAGER_LOADED, function (e) {
          return _this31.onAdsManagerLoaded(e);
        }, !1), _this31.loader.addEventListener(google.ima.AdErrorEvent.Type.AD_ERROR, function (e) {
          return _this31.onAdError(e);
        }, !1), _this31.requestAds();
      }), e(this, "requestAds", function () {
        var e = _this31.player.elements.container;

        try {
          var _t20 = new google.ima.AdsRequest();

          _t20.adTagUrl = _this31.tagUrl, _t20.linearAdSlotWidth = e.offsetWidth, _t20.linearAdSlotHeight = e.offsetHeight, _t20.nonLinearAdSlotWidth = e.offsetWidth, _t20.nonLinearAdSlotHeight = e.offsetHeight, _t20.forceNonLinearFullSlot = !1, _t20.setAdWillPlayMuted(!_this31.player.muted), _this31.loader.requestAds(_t20);
        } catch (e) {
          _this31.onAdError(e);
        }
      }), e(this, "pollCountdown", function () {
        var e = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : !1;
        if (!e) return clearInterval(_this31.countdownTimer), void _this31.elements.container.removeAttribute("data-badge-text");
        _this31.countdownTimer = setInterval(function () {
          var e = Be(Math.max(_this31.manager.getRemainingTime(), 0)),
              t = "".concat(De.get("advertisement", _this31.player.config), " - ").concat(e);

          _this31.elements.container.setAttribute("data-badge-text", t);
        }, 100);
      }), e(this, "onAdsManagerLoaded", function (e) {
        if (!_this31.enabled) return;
        var t = new google.ima.AdsRenderingSettings();
        t.restoreCustomPlaybackStateOnAdBreakComplete = !0, t.enablePreloading = !0, _this31.manager = e.getAdsManager(_this31.player, t), _this31.cuePoints = _this31.manager.getCuePoints(), _this31.manager.addEventListener(google.ima.AdErrorEvent.Type.AD_ERROR, function (e) {
          return _this31.onAdError(e);
        }), Object.keys(google.ima.AdEvent.Type).forEach(function (e) {
          _this31.manager.addEventListener(google.ima.AdEvent.Type[e], function (e) {
            return _this31.onAdEvent(e);
          });
        }), _this31.trigger("loaded");
      }), e(this, "addCuePoints", function () {
        W(_this31.cuePoints) || _this31.cuePoints.forEach(function (e) {
          if (0 !== e && -1 !== e && e < _this31.player.duration) {
            var _t21 = _this31.player.elements.progress;

            if (H(_t21)) {
              var _i18 = 100 / _this31.player.duration * e,
                  _s16 = Z("span", {
                class: _this31.player.config.classNames.cues
              });

              _s16.style.left = "".concat(_i18.toString(), "%"), _t21.appendChild(_s16);
            }
          }
        });
      }), e(this, "onAdEvent", function (e) {
        var t = _this31.player.elements.container,
            i = e.getAd(),
            s = e.getAdData();

        switch (function (e) {
          ve.call(_this31.player, _this31.player.media, "ads".concat(e.replace(/_/g, "").toLowerCase()));
        }(e.type), e.type) {
          case google.ima.AdEvent.Type.LOADED:
            _this31.trigger("loaded"), _this31.pollCountdown(!0), i.isLinear() || (i.width = t.offsetWidth, i.height = t.offsetHeight);
            break;

          case google.ima.AdEvent.Type.STARTED:
            _this31.manager.setVolume(_this31.player.volume);

            break;

          case google.ima.AdEvent.Type.ALL_ADS_COMPLETED:
            _this31.player.ended ? _this31.loadAds() : _this31.loader.contentComplete();
            break;

          case google.ima.AdEvent.Type.CONTENT_PAUSE_REQUESTED:
            _this31.pauseContent();

            break;

          case google.ima.AdEvent.Type.CONTENT_RESUME_REQUESTED:
            _this31.pollCountdown(), _this31.resumeContent();
            break;

          case google.ima.AdEvent.Type.LOG:
            s.adError && _this31.player.debug.warn("Non-fatal ad error: ".concat(s.adError.getMessage()));
        }
      }), e(this, "onAdError", function (e) {
        _this31.cancel(), _this31.player.debug.warn("Ads error", e);
      }), e(this, "listeners", function () {
        var e = _this31.player.elements.container;
        var t;
        _this31.player.on("canplay", function () {
          _this31.addCuePoints();
        }), _this31.player.on("ended", function () {
          _this31.loader.contentComplete();
        }), _this31.player.on("timeupdate", function () {
          t = _this31.player.currentTime;
        }), _this31.player.on("seeked", function () {
          var e = _this31.player.currentTime;
          W(_this31.cuePoints) || _this31.cuePoints.forEach(function (i, s) {
            t < i && i < e && (_this31.manager.discardAdBreak(), _this31.cuePoints.splice(s, 1));
          });
        }), window.addEventListener("resize", function () {
          _this31.manager && _this31.manager.resize(e.offsetWidth, e.offsetHeight, google.ima.ViewMode.NORMAL);
        });
      }), e(this, "play", function () {
        var e = _this31.player.elements.container;
        _this31.managerPromise || _this31.resumeContent(), _this31.managerPromise.then(function () {
          _this31.manager.setVolume(_this31.player.volume), _this31.elements.displayContainer.initialize();

          try {
            _this31.initialized || (_this31.manager.init(e.offsetWidth, e.offsetHeight, google.ima.ViewMode.NORMAL), _this31.manager.start()), _this31.initialized = !0;
          } catch (e) {
            _this31.onAdError(e);
          }
        }).catch(function () {});
      }), e(this, "resumeContent", function () {
        _this31.elements.container.style.zIndex = "", _this31.playing = !1, ke(_this31.player.media.play());
      }), e(this, "pauseContent", function () {
        _this31.elements.container.style.zIndex = 3, _this31.playing = !0, _this31.player.media.pause();
      }), e(this, "cancel", function () {
        _this31.initialized && _this31.resumeContent(), _this31.trigger("error"), _this31.loadAds();
      }), e(this, "loadAds", function () {
        _this31.managerPromise.then(function () {
          _this31.manager && _this31.manager.destroy(), _this31.managerPromise = new Promise(function (e) {
            _this31.on("loaded", e), _this31.player.debug.log(_this31.manager);
          }), _this31.initialized = !1, _this31.requestAds();
        }).catch(function () {});
      }), e(this, "trigger", function (e) {
        for (var _len4 = arguments.length, t = new Array(_len4 > 1 ? _len4 - 1 : 0), _key4 = 1; _key4 < _len4; _key4++) {
          t[_key4 - 1] = arguments[_key4];
        }

        var i = _this31.events[e];
        j(i) && i.forEach(function (e) {
          q(e) && e.apply(_this31, t);
        });
      }), e(this, "on", function (e, t) {
        return j(_this31.events[e]) || (_this31.events[e] = []), _this31.events[e].push(t), _this31;
      }), e(this, "startSafetyTimer", function (e, t) {
        _this31.player.debug.log("Safety timer invoked from: ".concat(t)), _this31.safetyTimer = setTimeout(function () {
          _this31.cancel(), _this31.clearSafetyTimer("startSafetyTimer()");
        }, e);
      }), e(this, "clearSafetyTimer", function (e) {
        I(_this31.safetyTimer) || (_this31.player.debug.log("Safety timer cleared from: ".concat(e)), clearTimeout(_this31.safetyTimer), _this31.safetyTimer = null);
      }), this.player = t, this.config = t.config.ads, this.playing = !1, this.initialized = !1, this.elements = {
        container: null,
        displayContainer: null
      }, this.manager = null, this.loader = null, this.cuePoints = null, this.events = {}, this.safetyTimer = null, this.countdownTimer = null, this.managerPromise = new Promise(function (e, t) {
        _this31.on("loaded", e), _this31.on("error", t);
      }), this.load();
    }

    _createClass(pt, [{
      key: "enabled",
      get: function get() {
        var e = this.config;
        return this.player.isHTML5 && this.player.isVideo && e.enabled && (!W(e.publisherId) || U(e.tagUrl));
      }
    }, {
      key: "tagUrl",
      get: function get() {
        var e = this.config;
        if (U(e.tagUrl)) return e.tagUrl;
        return "https://go.aniview.com/api/adserver6/vast/?".concat(ze({
          AV_PUBLISHERID: "58c25bb0073ef448b1087ad6",
          AV_CHANNELID: "5a0458dc28a06145e4519d21",
          AV_URL: window.location.hostname,
          cb: Date.now(),
          AV_WIDTH: 640,
          AV_HEIGHT: 480,
          AV_CDIM2: e.publisherId
        }));
      }
    }]);

    return pt;
  }();

  var gt = function gt(e) {
    var t = [];
    return e.split(/\r\n\r\n|\n\n|\r\r/).forEach(function (e) {
      var i = {};
      e.split(/\r\n|\n|\r/).forEach(function (e) {
        if ($(i.startTime)) {
          if (!W(e.trim()) && W(i.text)) {
            var _t23, _t24, _t22$1$split, _t22$1$split2;

            var _t22 = e.trim().split("#xywh=");

            (_t23 = _t22, _t24 = _slicedToArray(_t23, 1), i.text = _t24[0], _t23), _t22[1] && (_t22$1$split = _t22[1].split(","), _t22$1$split2 = _slicedToArray(_t22$1$split, 4), i.x = _t22$1$split2[0], i.y = _t22$1$split2[1], i.w = _t22$1$split2[2], i.h = _t22$1$split2[3], _t22$1$split);
          }
        } else {
          var _t25 = e.match(/([0-9]{2})?:?([0-9]{2}):([0-9]{2}).([0-9]{2,3})( ?--> ?)([0-9]{2})?:?([0-9]{2}):([0-9]{2}).([0-9]{2,3})/);

          _t25 && (i.startTime = 60 * Number(_t25[1] || 0) * 60 + 60 * Number(_t25[2]) + Number(_t25[3]) + Number("0.".concat(_t25[4])), i.endTime = 60 * Number(_t25[6] || 0) * 60 + 60 * Number(_t25[7]) + Number(_t25[8]) + Number("0.".concat(_t25[9])));
        }
      }), i.text && t.push(i);
    }), t;
  },
      ft = function ft(e, t) {
    var i = {};
    return e > t.width / t.height ? (i.width = t.width, i.height = 1 / e * t.width) : (i.height = t.height, i.width = e * t.height), i;
  };

  var bt = /*#__PURE__*/function () {
    function bt(t) {
      var _this32 = this;

      _classCallCheck(this, bt);

      e(this, "load", function () {
        _this32.player.elements.display.seekTooltip && (_this32.player.elements.display.seekTooltip.hidden = _this32.enabled), _this32.enabled && _this32.getThumbnails().then(function () {
          _this32.enabled && (_this32.render(), _this32.determineContainerAutoSizing(), _this32.loaded = !0);
        });
      }), e(this, "getThumbnails", function () {
        return new Promise(function (e) {
          var t = _this32.player.config.previewThumbnails.src;
          if (W(t)) throw new Error("Missing previewThumbnails.src config attribute");

          var i = function i() {
            _this32.thumbnails.sort(function (e, t) {
              return e.height - t.height;
            }), _this32.player.debug.log("Preview thumbnails", _this32.thumbnails), e();
          };

          if (q(t)) t(function (e) {
            _this32.thumbnails = e, i();
          });else {
            var _e27 = (_(t) ? [t] : t).map(function (e) {
              return _this32.getThumbnail(e);
            });

            Promise.all(_e27).then(i);
          }
        });
      }), e(this, "getThumbnail", function (e) {
        return new Promise(function (t) {
          Fe(e).then(function (i) {
            var s = {
              frames: gt(i),
              height: null,
              urlPrefix: ""
            };
            s.frames[0].text.startsWith("/") || s.frames[0].text.startsWith("http://") || s.frames[0].text.startsWith("https://") || (s.urlPrefix = e.substring(0, e.lastIndexOf("/") + 1));
            var n = new Image();
            n.onload = function () {
              s.height = n.naturalHeight, s.width = n.naturalWidth, _this32.thumbnails.push(s), t();
            }, n.src = s.urlPrefix + s.frames[0].text;
          });
        });
      }), e(this, "startMove", function (e) {
        if (_this32.loaded && F(e) && ["touchmove", "mousemove"].includes(e.type) && _this32.player.media.duration) {
          if ("touchmove" === e.type) _this32.seekTime = _this32.player.media.duration * (_this32.player.elements.inputs.seek.value / 100);else {
            var _t26 = _this32.player.elements.progress.getBoundingClientRect(),
                _i19 = 100 / _t26.width * (e.pageX - _t26.left);

            _this32.seekTime = _this32.player.media.duration * (_i19 / 100), _this32.seekTime < 0 && (_this32.seekTime = 0), _this32.seekTime > _this32.player.media.duration - 1 && (_this32.seekTime = _this32.player.media.duration - 1), _this32.mousePosX = e.pageX, _this32.elements.thumb.time.innerText = Be(_this32.seekTime);
          }

          _this32.showImageAtCurrentTime();
        }
      }), e(this, "endMove", function () {
        _this32.toggleThumbContainer(!1, !0);
      }), e(this, "startScrubbing", function (e) {
        (I(e.button) || !1 === e.button || 0 === e.button) && (_this32.mouseDown = !0, _this32.player.media.duration && (_this32.toggleScrubbingContainer(!0), _this32.toggleThumbContainer(!1, !0), _this32.showImageAtCurrentTime()));
      }), e(this, "endScrubbing", function () {
        _this32.mouseDown = !1, Math.ceil(_this32.lastTime) === Math.ceil(_this32.player.media.currentTime) ? _this32.toggleScrubbingContainer(!1) : ye.call(_this32.player, _this32.player.media, "timeupdate", function () {
          _this32.mouseDown || _this32.toggleScrubbingContainer(!1);
        });
      }), e(this, "listeners", function () {
        _this32.player.on("play", function () {
          _this32.toggleThumbContainer(!1, !0);
        }), _this32.player.on("seeked", function () {
          _this32.toggleThumbContainer(!1);
        }), _this32.player.on("timeupdate", function () {
          _this32.lastTime = _this32.player.media.currentTime;
        });
      }), e(this, "render", function () {
        _this32.elements.thumb.container = Z("div", {
          class: _this32.player.config.classNames.previewThumbnails.thumbContainer
        }), _this32.elements.thumb.imageContainer = Z("div", {
          class: _this32.player.config.classNames.previewThumbnails.imageContainer
        }), _this32.elements.thumb.container.appendChild(_this32.elements.thumb.imageContainer);
        var e = Z("div", {
          class: _this32.player.config.classNames.previewThumbnails.timeContainer
        });
        _this32.elements.thumb.time = Z("span", {}, "00:00"), e.appendChild(_this32.elements.thumb.time), _this32.elements.thumb.container.appendChild(e), H(_this32.player.elements.progress) && _this32.player.elements.progress.appendChild(_this32.elements.thumb.container), _this32.elements.scrubbing.container = Z("div", {
          class: _this32.player.config.classNames.previewThumbnails.scrubbingContainer
        }), _this32.player.elements.wrapper.appendChild(_this32.elements.scrubbing.container);
      }), e(this, "destroy", function () {
        _this32.elements.thumb.container && _this32.elements.thumb.container.remove(), _this32.elements.scrubbing.container && _this32.elements.scrubbing.container.remove();
      }), e(this, "showImageAtCurrentTime", function () {
        _this32.mouseDown ? _this32.setScrubbingContainerSize() : _this32.setThumbContainerSizeAndPos();

        var e = _this32.thumbnails[0].frames.findIndex(function (e) {
          return _this32.seekTime >= e.startTime && _this32.seekTime <= e.endTime;
        }),
            t = e >= 0;

        var i = 0;
        _this32.mouseDown || _this32.toggleThumbContainer(t), t && (_this32.thumbnails.forEach(function (t, s) {
          _this32.loadedImages.includes(t.frames[e].text) && (i = s);
        }), e !== _this32.showingThumb && (_this32.showingThumb = e, _this32.loadImage(i)));
      }), e(this, "loadImage", function () {
        var e = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : 0;
        var t = _this32.showingThumb,
            i = _this32.thumbnails[e],
            s = i.urlPrefix,
            n = i.frames[t],
            a = i.frames[t].text,
            l = s + a;
        if (_this32.currentImageElement && _this32.currentImageElement.dataset.filename === a) _this32.showImage(_this32.currentImageElement, n, e, t, a, !1), _this32.currentImageElement.dataset.index = t, _this32.removeOldImages(_this32.currentImageElement);else {
          _this32.loadingImage && _this32.usingSprites && (_this32.loadingImage.onload = null);

          var _i20 = new Image();

          _i20.src = l, _i20.dataset.index = t, _i20.dataset.filename = a, _this32.showingThumbFilename = a, _this32.player.debug.log("Loading image: ".concat(l)), _i20.onload = function () {
            return _this32.showImage(_i20, n, e, t, a, !0);
          }, _this32.loadingImage = _i20, _this32.removeOldImages(_i20);
        }
      }), e(this, "showImage", function (e, t, i, s, n) {
        var a = arguments.length > 5 && arguments[5] !== undefined ? arguments[5] : !0;
        _this32.player.debug.log("Showing thumb: ".concat(n, ". num: ").concat(s, ". qual: ").concat(i, ". newimg: ").concat(a)), _this32.setImageSizeAndOffset(e, t), a && (_this32.currentImageContainer.appendChild(e), _this32.currentImageElement = e, _this32.loadedImages.includes(n) || _this32.loadedImages.push(n)), _this32.preloadNearby(s, !0).then(_this32.preloadNearby(s, !1)).then(_this32.getHigherQuality(i, e, t, n));
      }), e(this, "removeOldImages", function (e) {
        Array.from(_this32.currentImageContainer.children).forEach(function (t) {
          if ("img" !== t.tagName.toLowerCase()) return;
          var i = _this32.usingSprites ? 500 : 1e3;

          if (t.dataset.index !== e.dataset.index && !t.dataset.deleting) {
            t.dataset.deleting = !0;
            var _e28 = _this32.currentImageContainer;
            setTimeout(function () {
              _e28.removeChild(t), _this32.player.debug.log("Removing thumb: ".concat(t.dataset.filename));
            }, i);
          }
        });
      }), e(this, "preloadNearby", function (e) {
        var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : !0;
        return new Promise(function (i) {
          setTimeout(function () {
            var s = _this32.thumbnails[0].frames[e].text;

            if (_this32.showingThumbFilename === s) {
              var _n8;

              _n8 = t ? _this32.thumbnails[0].frames.slice(e) : _this32.thumbnails[0].frames.slice(0, e).reverse();

              var _a6 = !1;

              _n8.forEach(function (e) {
                var t = e.text;

                if (t !== s && !_this32.loadedImages.includes(t)) {
                  _a6 = !0, _this32.player.debug.log("Preloading thumb filename: ".concat(t));

                  var _e29 = _this32.thumbnails[0].urlPrefix,
                      _s17 = _e29 + t,
                      _n9 = new Image();

                  _n9.src = _s17, _n9.onload = function () {
                    _this32.player.debug.log("Preloaded thumb filename: ".concat(t)), _this32.loadedImages.includes(t) || _this32.loadedImages.push(t), i();
                  };
                }
              }), _a6 || i();
            }
          }, 300);
        });
      }), e(this, "getHigherQuality", function (e, t, i, s) {
        if (e < _this32.thumbnails.length - 1) {
          var _n10 = t.naturalHeight;
          _this32.usingSprites && (_n10 = i.h), _n10 < _this32.thumbContainerHeight && setTimeout(function () {
            _this32.showingThumbFilename === s && (_this32.player.debug.log("Showing higher quality thumb for: ".concat(s)), _this32.loadImage(e + 1));
          }, 300);
        }
      }), e(this, "toggleThumbContainer", function () {
        var e = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : !1;
        var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : !1;
        var i = _this32.player.config.classNames.previewThumbnails.thumbContainerShown;
        _this32.elements.thumb.container.classList.toggle(i, e), !e && t && (_this32.showingThumb = null, _this32.showingThumbFilename = null);
      }), e(this, "toggleScrubbingContainer", function () {
        var e = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : !1;
        var t = _this32.player.config.classNames.previewThumbnails.scrubbingContainerShown;
        _this32.elements.scrubbing.container.classList.toggle(t, e), e || (_this32.showingThumb = null, _this32.showingThumbFilename = null);
      }), e(this, "determineContainerAutoSizing", function () {
        (_this32.elements.thumb.imageContainer.clientHeight > 20 || _this32.elements.thumb.imageContainer.clientWidth > 20) && (_this32.sizeSpecifiedInCSS = !0);
      }), e(this, "setThumbContainerSizeAndPos", function () {
        if (_this32.sizeSpecifiedInCSS) {
          if (_this32.elements.thumb.imageContainer.clientHeight > 20 && _this32.elements.thumb.imageContainer.clientWidth < 20) {
            var _e30 = Math.floor(_this32.elements.thumb.imageContainer.clientHeight * _this32.thumbAspectRatio);

            _this32.elements.thumb.imageContainer.style.width = "".concat(_e30, "px");
          } else if (_this32.elements.thumb.imageContainer.clientHeight < 20 && _this32.elements.thumb.imageContainer.clientWidth > 20) {
            var _e31 = Math.floor(_this32.elements.thumb.imageContainer.clientWidth / _this32.thumbAspectRatio);

            _this32.elements.thumb.imageContainer.style.height = "".concat(_e31, "px");
          }
        } else {
          var _e32 = Math.floor(_this32.thumbContainerHeight * _this32.thumbAspectRatio);

          _this32.elements.thumb.imageContainer.style.height = "".concat(_this32.thumbContainerHeight, "px"), _this32.elements.thumb.imageContainer.style.width = "".concat(_e32, "px");
        }

        _this32.setThumbContainerPos();
      }), e(this, "setThumbContainerPos", function () {
        var e = _this32.player.elements.progress.getBoundingClientRect(),
            t = _this32.player.elements.container.getBoundingClientRect(),
            i = _this32.elements.thumb.container,
            s = t.left - e.left + 10,
            n = t.right - e.left - i.clientWidth - 10;

        var a = _this32.mousePosX - e.left - i.clientWidth / 2;
        a < s && (a = s), a > n && (a = n), i.style.left = "".concat(a, "px");
      }), e(this, "setScrubbingContainerSize", function () {
        var _ft = ft(_this32.thumbAspectRatio, {
          width: _this32.player.media.clientWidth,
          height: _this32.player.media.clientHeight
        }),
            e = _ft.width,
            t = _ft.height;

        _this32.elements.scrubbing.container.style.width = "".concat(e, "px"), _this32.elements.scrubbing.container.style.height = "".concat(t, "px");
      }), e(this, "setImageSizeAndOffset", function (e, t) {
        if (!_this32.usingSprites) return;
        var i = _this32.thumbContainerHeight / t.h;
        e.style.height = e.naturalHeight * i + "px", e.style.width = e.naturalWidth * i + "px", e.style.left = "-".concat(t.x * i, "px"), e.style.top = "-".concat(t.y * i, "px");
      }), this.player = t, this.thumbnails = [], this.loaded = !1, this.lastMouseMoveTime = Date.now(), this.mouseDown = !1, this.loadedImages = [], this.elements = {
        thumb: {},
        scrubbing: {}
      }, this.load();
    }

    _createClass(bt, [{
      key: "enabled",
      get: function get() {
        return this.player.isHTML5 && this.player.isVideo && this.player.config.previewThumbnails.enabled;
      }
    }, {
      key: "currentImageContainer",
      get: function get() {
        return this.mouseDown ? this.elements.scrubbing.container : this.elements.thumb.imageContainer;
      }
    }, {
      key: "usingSprites",
      get: function get() {
        return Object.keys(this.thumbnails[0].frames[0]).includes("w");
      }
    }, {
      key: "thumbAspectRatio",
      get: function get() {
        return this.usingSprites ? this.thumbnails[0].frames[0].w / this.thumbnails[0].frames[0].h : this.thumbnails[0].width / this.thumbnails[0].height;
      }
    }, {
      key: "thumbContainerHeight",
      get: function get() {
        if (this.mouseDown) {
          var _ft2 = ft(this.thumbAspectRatio, {
            width: this.player.media.clientWidth,
            height: this.player.media.clientHeight
          }),
              _e33 = _ft2.height;

          return _e33;
        }

        return this.sizeSpecifiedInCSS ? this.elements.thumb.imageContainer.clientHeight : Math.floor(this.player.media.clientWidth / this.thumbAspectRatio / 4);
      }
    }, {
      key: "currentImageElement",
      get: function get() {
        return this.mouseDown ? this.currentScrubbingImageElement : this.currentThumbnailImageElement;
      },
      set: function set(e) {
        this.mouseDown ? this.currentScrubbingImageElement = e : this.currentThumbnailImageElement = e;
      }
    }]);

    return bt;
  }();

  var yt = {
    insertElements: function insertElements(e, t) {
      var _this33 = this;

      _(t) ? ee(e, this.media, {
        src: t
      }) : j(t) && t.forEach(function (t) {
        ee(e, _this33.media, t);
      });
    },
    change: function change(e) {
      var _this34 = this;

      Q(e, "sources.length") ? (Ie.cancelRequests.call(this), this.destroy.call(this, function () {
        _this34.options.quality = [], te(_this34.media), _this34.media = null, H(_this34.elements.container) && _this34.elements.container.removeAttribute("class");

        var t = e.sources,
            i = e.type,
            _t27 = _slicedToArray(t, 1),
            _t27$ = _t27[0],
            _t27$$provider = _t27$.provider,
            s = _t27$$provider === void 0 ? Je.html5 : _t27$$provider,
            n = _t27$.src,
            a = "html5" === s ? i : "div",
            l = "html5" === s ? {} : {
          src: n
        };

        Object.assign(_this34, {
          provider: s,
          type: i,
          supported: me.check(i, s, _this34.config.playsinline),
          media: Z(a, l)
        }), _this34.elements.container.appendChild(_this34.media), O(e.autoplay) && (_this34.config.autoplay = e.autoplay), _this34.isHTML5 && (_this34.config.crossorigin && _this34.media.setAttribute("crossorigin", ""), _this34.config.autoplay && _this34.media.setAttribute("autoplay", ""), W(e.poster) || (_this34.poster = e.poster), _this34.config.loop.active && _this34.media.setAttribute("loop", ""), _this34.config.muted && _this34.media.setAttribute("muted", ""), _this34.config.playsinline && _this34.media.setAttribute("playsinline", "")), nt.addStyleHook.call(_this34), _this34.isHTML5 && yt.insertElements.call(_this34, "source", t), _this34.config.title = e.title, mt.setup.call(_this34), _this34.isHTML5 && Object.keys(e).includes("tracks") && yt.insertElements.call(_this34, "track", e.tracks), (_this34.isHTML5 || _this34.isEmbed && !_this34.supported.ui) && nt.build.call(_this34), _this34.isHTML5 && _this34.media.load(), W(e.previewThumbnails) || (Object.assign(_this34.config.previewThumbnails, e.previewThumbnails), _this34.previewThumbnails && _this34.previewThumbnails.loaded && (_this34.previewThumbnails.destroy(), _this34.previewThumbnails = null), _this34.config.previewThumbnails.enabled && (_this34.previewThumbnails = new bt(_this34))), _this34.fullscreen.update();
      }, !0)) : this.debug.warn("Invalid source format");
    }
  };

  var vt = /*#__PURE__*/function () {
    function vt(t, i) {
      var _this35 = this;

      _classCallCheck(this, vt);

      if (e(this, "play", function () {
        return q(_this35.media.play) ? (_this35.ads && _this35.ads.enabled && _this35.ads.managerPromise.then(function () {
          return _this35.ads.play();
        }).catch(function () {
          return ke(_this35.media.play());
        }), _this35.media.play()) : null;
      }), e(this, "pause", function () {
        return _this35.playing && q(_this35.media.pause) ? _this35.media.pause() : null;
      }), e(this, "togglePlay", function (e) {
        return (O(e) ? e : !_this35.playing) ? _this35.play() : _this35.pause();
      }), e(this, "stop", function () {
        _this35.isHTML5 ? (_this35.pause(), _this35.restart()) : q(_this35.media.stop) && _this35.media.stop();
      }), e(this, "restart", function () {
        _this35.currentTime = 0;
      }), e(this, "rewind", function (e) {
        _this35.currentTime -= $(e) ? e : _this35.config.seekTime;
      }), e(this, "forward", function (e) {
        _this35.currentTime += $(e) ? e : _this35.config.seekTime;
      }), e(this, "increaseVolume", function (e) {
        var t = _this35.media.muted ? 0 : _this35.volume;
        _this35.volume = t + ($(e) ? e : 0);
      }), e(this, "decreaseVolume", function (e) {
        _this35.increaseVolume(-e);
      }), e(this, "airplay", function () {
        me.airplay && _this35.media.webkitShowPlaybackTargetPicker();
      }), e(this, "toggleControls", function (e) {
        if (_this35.supported.ui && !_this35.isAudio) {
          var _t28 = oe(_this35.elements.container, _this35.config.classNames.hideControls),
              _i21 = void 0 === e ? void 0 : !e,
              _s18 = le(_this35.elements.container, _this35.config.classNames.hideControls, _i21);

          if (_s18 && j(_this35.config.controls) && _this35.config.controls.includes("settings") && !W(_this35.config.settings) && Ue.toggleMenu.call(_this35, !1), _s18 !== _t28) {
            var _e34 = _s18 ? "controlshidden" : "controlsshown";

            ve.call(_this35, _this35.media, _e34);
          }

          return !_s18;
        }

        return !1;
      }), e(this, "on", function (e, t) {
        fe.call(_this35, _this35.elements.container, e, t);
      }), e(this, "once", function (e, t) {
        ye.call(_this35, _this35.elements.container, e, t);
      }), e(this, "off", function (e, t) {
        be(_this35.elements.container, e, t);
      }), e(this, "destroy", function (e) {
        var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : !1;
        if (!_this35.ready) return;

        var i = function i() {
          document.body.style.overflow = "", _this35.embed = null, t ? (Object.keys(_this35.elements).length && (te(_this35.elements.buttons.play), te(_this35.elements.captions), te(_this35.elements.controls), te(_this35.elements.wrapper), _this35.elements.buttons.play = null, _this35.elements.captions = null, _this35.elements.controls = null, _this35.elements.wrapper = null), q(e) && e()) : (we.call(_this35), Ie.cancelRequests.call(_this35), se(_this35.elements.original, _this35.elements.container), ve.call(_this35, _this35.elements.original, "destroyed", !0), q(e) && e.call(_this35.elements.original), _this35.ready = !1, setTimeout(function () {
            _this35.elements = null, _this35.media = null;
          }, 200));
        };

        _this35.stop(), clearTimeout(_this35.timers.loading), clearTimeout(_this35.timers.controls), clearTimeout(_this35.timers.resized), _this35.isHTML5 ? (nt.toggleNativeControls.call(_this35, !0), i()) : _this35.isYouTube ? (clearInterval(_this35.timers.buffering), clearInterval(_this35.timers.playing), null !== _this35.embed && q(_this35.embed.destroy) && _this35.embed.destroy(), i()) : _this35.isVimeo && (null !== _this35.embed && _this35.embed.unload().then(i), setTimeout(i, 200));
      }), e(this, "supports", function (e) {
        return me.mime.call(_this35, e);
      }), this.timers = {}, this.ready = !1, this.loading = !1, this.failed = !1, this.touch = me.touch, this.media = t, _(this.media) && (this.media = document.querySelectorAll(this.media)), (window.jQuery && this.media instanceof jQuery || D(this.media) || j(this.media)) && (this.media = this.media[0]), this.config = X({}, Ye, vt.defaults, i || {}, function () {
        try {
          return JSON.parse(_this35.media.getAttribute("data-plyr-config"));
        } catch (e) {
          return {};
        }
      }()), this.elements = {
        container: null,
        fullscreen: null,
        captions: null,
        buttons: {},
        display: {},
        progress: {},
        inputs: {},
        settings: {
          popup: null,
          menu: null,
          panels: {},
          buttons: {}
        }
      }, this.captions = {
        active: null,
        currentTrack: -1,
        meta: new WeakMap()
      }, this.fullscreen = {
        active: !1
      }, this.options = {
        speed: [],
        quality: []
      }, this.debug = new tt(this.config.debug), this.debug.log("Config", this.config), this.debug.log("Support", me), I(this.media) || !H(this.media)) return void this.debug.error("Setup failed: no suitable element passed");
      if (this.media.plyr) return void this.debug.warn("Target already setup");
      if (!this.config.enabled) return void this.debug.error("Setup failed: disabled by config");
      if (!me.check().api) return void this.debug.error("Setup failed: no support");
      var s = this.media.cloneNode(!0);
      s.autoplay = !1, this.elements.original = s;
      var n = this.media.tagName.toLowerCase();
      var a = null,
          l = null;

      switch (n) {
        case "div":
          if (a = this.media.querySelector("iframe"), H(a)) {
            if (l = We(a.getAttribute("src")), this.provider = function (e) {
              return /^(https?:\/\/)?(www\.)?(youtube\.com|youtube-nocookie\.com|youtu\.?be)\/.+$/.test(e) ? Je.youtube : /^https?:\/\/player.vimeo.com\/video\/\d{0,9}(?=\b|\/)/.test(e) ? Je.vimeo : null;
            }(l.toString()), this.elements.container = this.media, this.media = a, this.elements.container.className = "", l.search.length) {
              var _e35 = ["1", "true"];
              _e35.includes(l.searchParams.get("autoplay")) && (this.config.autoplay = !0), _e35.includes(l.searchParams.get("loop")) && (this.config.loop.active = !0), this.isYouTube ? (this.config.playsinline = _e35.includes(l.searchParams.get("playsinline")), this.config.youtube.hl = l.searchParams.get("hl")) : this.config.playsinline = !0;
            }
          } else this.provider = this.media.getAttribute(this.config.attributes.embed.provider), this.media.removeAttribute(this.config.attributes.embed.provider);

          if (W(this.provider) || !Object.values(Je).includes(this.provider)) return void this.debug.error("Setup failed: Invalid provider");
          this.type = Ze;
          break;

        case "video":
        case "audio":
          this.type = n, this.provider = Je.html5, this.media.hasAttribute("crossorigin") && (this.config.crossorigin = !0), this.media.hasAttribute("autoplay") && (this.config.autoplay = !0), (this.media.hasAttribute("playsinline") || this.media.hasAttribute("webkit-playsinline")) && (this.config.playsinline = !0), this.media.hasAttribute("muted") && (this.config.muted = !0), this.media.hasAttribute("loop") && (this.config.loop.active = !0);
          break;

        default:
          return void this.debug.error("Setup failed: unsupported type");
      }

      this.supported = me.check(this.type, this.provider, this.config.playsinline), this.supported.api ? (this.eventListeners = [], this.listeners = new at(this), this.storage = new He(this), this.media.plyr = this, H(this.elements.container) || (this.elements.container = Z("div", {
        tabindex: 0
      }), J(this.media, this.elements.container)), nt.migrateStyles.call(this), nt.addStyleHook.call(this), mt.setup.call(this), this.config.debug && fe.call(this, this.elements.container, this.config.events.join(" "), function (e) {
        _this35.debug.log("event: ".concat(e.type));
      }), this.fullscreen = new it(this), (this.isHTML5 || this.isEmbed && !this.supported.ui) && nt.build.call(this), this.listeners.container(), this.listeners.global(), this.config.ads.enabled && (this.ads = new pt(this)), this.isHTML5 && this.config.autoplay && this.once("canplay", function () {
        return ke(_this35.play());
      }), this.lastSeekTime = 0, this.config.previewThumbnails.enabled && (this.previewThumbnails = new bt(this))) : this.debug.error("Setup failed: no support");
    }

    _createClass(vt, [{
      key: "isHTML5",
      get: function get() {
        return this.provider === Je.html5;
      }
    }, {
      key: "isEmbed",
      get: function get() {
        return this.isYouTube || this.isVimeo;
      }
    }, {
      key: "isYouTube",
      get: function get() {
        return this.provider === Je.youtube;
      }
    }, {
      key: "isVimeo",
      get: function get() {
        return this.provider === Je.vimeo;
      }
    }, {
      key: "isVideo",
      get: function get() {
        return this.type === Ze;
      }
    }, {
      key: "isAudio",
      get: function get() {
        return this.type === Ge;
      }
    }, {
      key: "playing",
      get: function get() {
        return Boolean(this.ready && !this.paused && !this.ended);
      }
    }, {
      key: "paused",
      get: function get() {
        return Boolean(this.media.paused);
      }
    }, {
      key: "stopped",
      get: function get() {
        return Boolean(this.paused && 0 === this.currentTime);
      }
    }, {
      key: "ended",
      get: function get() {
        return Boolean(this.media.ended);
      }
    }, {
      key: "currentTime",
      get: function get() {
        return Number(this.media.currentTime);
      },
      set: function set(e) {
        if (!this.duration) return;
        var t = $(e) && e > 0;
        this.media.currentTime = t ? Math.min(e, this.duration) : 0, this.debug.log("Seeking to ".concat(this.currentTime, " seconds"));
      }
    }, {
      key: "buffered",
      get: function get() {
        var e = this.media.buffered;
        return $(e) ? e : e && e.length && this.duration > 0 ? e.end(0) / this.duration : 0;
      }
    }, {
      key: "seeking",
      get: function get() {
        return Boolean(this.media.seeking);
      }
    }, {
      key: "duration",
      get: function get() {
        var e = parseFloat(this.config.duration),
            t = (this.media || {}).duration,
            i = $(t) && t !== 1 / 0 ? t : 0;
        return e || i;
      }
    }, {
      key: "volume",
      get: function get() {
        return Number(this.media.volume);
      },
      set: function set(e) {
        var _this$config2;

        var t = e;
        _(t) && (t = Number(t)), $(t) || (t = this.storage.get("volume")), $(t) || (_this$config2 = this.config, t = _this$config2.volume, _this$config2), t > 1 && (t = 1), t < 0 && (t = 0), this.config.volume = t, this.media.volume = t, !W(e) && this.muted && t > 0 && (this.muted = !1);
      }
    }, {
      key: "muted",
      get: function get() {
        return Boolean(this.media.muted);
      },
      set: function set(e) {
        var t = e;
        O(t) || (t = this.storage.get("muted")), O(t) || (t = this.config.muted), this.config.muted = t, this.media.muted = t;
      }
    }, {
      key: "hasAudio",
      get: function get() {
        return !this.isHTML5 || !!this.isAudio || Boolean(this.media.mozHasAudio) || Boolean(this.media.webkitAudioDecodedByteCount) || Boolean(this.media.audioTracks && this.media.audioTracks.length);
      }
    }, {
      key: "speed",
      get: function get() {
        return Number(this.media.playbackRate);
      },
      set: function set(e) {
        var _this36 = this;

        var t = null;
        $(e) && (t = e), $(t) || (t = this.storage.get("speed")), $(t) || (t = this.config.speed.selected);
        var i = this.minimumSpeed,
            s = this.maximumSpeed;
        t = function () {
          var e = arguments.length > 0 && arguments[0] !== undefined ? arguments[0] : 0;
          var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : 0;
          var i = arguments.length > 2 && arguments[2] !== undefined ? arguments[2] : 255;
          return Math.min(Math.max(e, t), i);
        }(t, i, s), this.config.speed.selected = t, setTimeout(function () {
          _this36.media.playbackRate = t;
        }, 0);
      }
    }, {
      key: "minimumSpeed",
      get: function get() {
        return this.isYouTube ? Math.min.apply(Math, _toConsumableArray(this.options.speed)) : this.isVimeo ? .5 : .0625;
      }
    }, {
      key: "maximumSpeed",
      get: function get() {
        return this.isYouTube ? Math.max.apply(Math, _toConsumableArray(this.options.speed)) : this.isVimeo ? 2 : 16;
      }
    }, {
      key: "quality",
      get: function get() {
        return this.media.quality;
      },
      set: function set(e) {
        var t = this.config.quality,
            i = this.options.quality;
        if (!i.length) return;
        var s = [!W(e) && Number(e), this.storage.get("quality"), t.selected, t.default].find($),
            n = !0;

        if (!i.includes(s)) {
          var _e36 = Ae(i, s);

          this.debug.warn("Unsupported quality option: ".concat(s, ", using ").concat(_e36, " instead")), s = _e36, n = !1;
        }

        t.selected = s, this.media.quality = s, n && this.storage.set({
          quality: s
        });
      }
    }, {
      key: "loop",
      get: function get() {
        return Boolean(this.media.loop);
      },
      set: function set(e) {
        var t = O(e) ? e : this.config.loop.active;
        this.config.loop.active = t, this.media.loop = t;
      }
    }, {
      key: "source",
      get: function get() {
        return this.media.currentSrc;
      },
      set: function set(e) {
        yt.change.call(this, e);
      }
    }, {
      key: "download",
      get: function get() {
        var e = this.config.urls.download;
        return U(e) ? e : this.source;
      },
      set: function set(e) {
        U(e) && (this.config.urls.download = e, Ue.setDownloadUrl.call(this));
      }
    }, {
      key: "poster",
      get: function get() {
        return this.isVideo ? this.media.getAttribute("poster") || this.media.getAttribute("data-poster") : null;
      },
      set: function set(e) {
        this.isVideo ? nt.setPoster.call(this, e, !1).catch(function () {}) : this.debug.warn("Poster can only be set for video");
      }
    }, {
      key: "ratio",
      get: function get() {
        if (!this.isVideo) return null;
        var e = Pe(Ne.call(this));
        return j(e) ? e.join(":") : e;
      },
      set: function set(e) {
        this.isVideo ? _(e) && Ee(e) ? (this.config.ratio = Pe(e), Me.call(this)) : this.debug.error("Invalid aspect ratio specified (".concat(e, ")")) : this.debug.warn("Aspect ratio can only be set for video");
      }
    }, {
      key: "autoplay",
      get: function get() {
        return Boolean(this.config.autoplay);
      },
      set: function set(e) {
        var t = O(e) ? e : this.config.autoplay;
        this.config.autoplay = t;
      }
    }, {
      key: "toggleCaptions",
      value: function toggleCaptions(e) {
        Ke.toggle.call(this, e, !1);
      }
    }, {
      key: "currentTrack",
      get: function get() {
        var _this$captions2 = this.captions,
            e = _this$captions2.toggled,
            t = _this$captions2.currentTrack;
        return e ? t : -1;
      },
      set: function set(e) {
        Ke.set.call(this, e, !1);
      }
    }, {
      key: "language",
      get: function get() {
        return (Ke.getCurrentTrack.call(this) || {}).language;
      },
      set: function set(e) {
        Ke.setLanguage.call(this, e, !1);
      }
    }, {
      key: "pip",
      get: function get() {
        return me.pip ? W(this.media.webkitPresentationMode) ? this.media === document.pictureInPictureElement : this.media.webkitPresentationMode === Qe : null;
      },
      set: function set(e) {
        if (!me.pip) return;
        var t = O(e) ? e : !this.pip;
        q(this.media.webkitSetPresentationMode) && this.media.webkitSetPresentationMode(t ? Qe : Xe), q(this.media.requestPictureInPicture) && (!this.pip && t ? this.media.requestPictureInPicture() : this.pip && !t && document.exitPictureInPicture());
      }
    }], [{
      key: "supported",
      value: function supported(e, t, i) {
        return me.check(e, t, i);
      }
    }, {
      key: "loadSprite",
      value: function loadSprite(e, t) {
        return Re(e, t);
      }
    }, {
      key: "setup",
      value: function setup(e) {
        var t = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : {};
        var i = null;
        return _(e) ? i = Array.from(document.querySelectorAll(e)) : D(e) ? i = Array.from(e) : j(e) && (i = e.filter(H)), W(i) ? null : i.map(function (e) {
          return new vt(e, t);
        });
      }
    }]);

    return vt;
  }();

  var wt;
  return vt.defaults = (wt = Ye, JSON.parse(JSON.stringify(wt))), vt;
});
