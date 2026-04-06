export default class FullscreenPlugin {
  constructor() {
    function toggleFullScreen() {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen();
      } else {
        document.exitFullscreen();
      }
    }

    document.addEventListener("keydown", function(e) {
      if (e.key.toLowerCase() === "f" && e.ctrlKey && e.shiftKey) {
        e.preventDefault();
        toggleFullScreen();
      }
    });
  }
}
