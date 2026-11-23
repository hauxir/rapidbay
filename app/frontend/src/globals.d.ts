// Globals provided by the vendored scripts in app/frontend/lib. The npm
// packages behind the type imports are pinned to the same versions.

declare const Vue: typeof import("vue").default;
type Vue = import("vue").default;
type ComponentOptions<V extends Vue> = import("vue").ComponentOptions<V>;

declare const Hls: typeof import("hls.js").default;
type Hls = import("hls.js").default;

// navigo 6.0.2 ships no type declarations; only what app.ts uses.
type NavigoParams = { [key: string]: string } | null;
declare class Navigo {
    constructor(root?: string | null, useHash?: boolean);
    root: string;
    on(routes: { [route: string]: (params: NavigoParams) => void }): Navigo;
    resolve(): void;
    navigate(path: string): Navigo;
    historyAPIUpdateMethod(method: "pushState" | "replaceState"): void;
    lastRouteResolved(): { url: string; query: string };
}

interface ChromecastMedia {
    content: string;
    title?: string;
    time?: number;
    subtitles?: { active: boolean; src: string | null }[];
}
declare class ChromecastJS {
    cast(media: ChromecastMedia, callback?: (error?: unknown) => void): void;
}

interface Window {
    isSafari: boolean;
    isChrome: boolean;
}

// Vendor-prefixed Fullscreen API, still needed by older Firefox and Safari.
interface Document {
    mozFullScreenElement?: Element | null;
    webkitFullscreenElement?: Element | null;
    cancelFullScreen?: () => void;
    mozCancelFullScreen?: () => void;
    webkitCancelFullScreen?: () => void;
}
interface HTMLElement {
    mozRequestFullScreen?: () => void;
    webkitRequestFullscreen?: (options?: number) => void;
}

// The DOM typings dropped the title argument, which older browsers require.
interface NavigatorContentUtils {
    registerProtocolHandler(scheme: string, url: string, title: string): void;
}
