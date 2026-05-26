let captureCount = 0;

chrome.commands.onCommand.addListener((command) => {
  if (command === "capture_page") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs[0]) return;
      const tabId = tabs[0].id;

      // Capture the visible tab
      chrome.tabs.captureVisibleTab(null, { format: "png" }, (dataUrl) => {
        if (chrome.runtime.lastError) {
          console.error(chrome.runtime.lastError);
          return;
        }

        captureCount++;
        const filename = `snap_${String(captureCount).padStart(4, '0')}.png`;

        chrome.downloads.download({
          url: dataUrl,
          filename: filename,
          saveAs: false
        }, (downloadId) => {
          if (chrome.runtime.lastError) {
            console.error(chrome.runtime.lastError);
          }
        });

        // Show a quick flash effect on the page
        chrome.scripting.executeScript({
          target: { tabId: tabId },
          func: () => {
            const flash = document.createElement("div");
            flash.style.position = "fixed";
            flash.style.top = "0";
            flash.style.left = "0";
            flash.style.width = "100%";
            flash.style.height = "100%";
            flash.style.backgroundColor = "white";
            flash.style.opacity = "0.6";
            flash.style.zIndex = "999999";
            flash.style.pointerEvents = "none";
            document.body.appendChild(flash);

            setTimeout(() => {
              flash.style.transition = "opacity 0.2s";
              flash.style.opacity = "0";
              setTimeout(() => flash.remove(), 200);
            }, 80);
          }
        });
      });
    });
  }
});