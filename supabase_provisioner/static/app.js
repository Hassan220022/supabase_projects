(function () {
  function showFlash(level, message) {
    var slot = document.querySelector("[data-flash-slot]");
    if (!slot) {
      return;
    }
    slot.innerHTML = "";
    var flash = document.createElement("div");
    flash.className = "flash flash-" + level;
    flash.setAttribute("role", "status");
    flash.textContent = message;
    slot.appendChild(flash);
  }

  function setSubmitting(form, submitting) {
    var submitButton = form.querySelector("button[type='submit'], button:not([type])");
    if (!submitButton) {
      return;
    }
    if (submitting) {
      submitButton.dataset.originalText = submitButton.textContent;
      submitButton.textContent = submitButton.dataset.loadingText || "Working...";
      submitButton.disabled = true;
      return;
    }
    submitButton.textContent = submitButton.dataset.originalText || submitButton.textContent;
    submitButton.disabled = false;
  }

  async function submitInPage(form) {
    setSubmitting(form, true);
    showFlash("info", form.dataset.pendingMessage || "Running action...");
    try {
      var response = await fetch(form.action, {
        method: (form.method || "post").toUpperCase(),
        body: new FormData(form),
        credentials: "same-origin",
        headers: {
          Accept: "text/html",
          "X-Requested-With": "fetch",
        },
      });

      var contentType = response.headers.get("content-type") || "";
      if (contentType.indexOf("text/html") !== -1) {
        var html = await response.text();
        var finalUrl = new URL(response.url || window.location.href, window.location.origin);
        history.pushState(null, "", finalUrl.pathname + finalUrl.search + finalUrl.hash);
        document.open();
        document.write(html);
        document.close();
        return;
      }

      if (!response.ok) {
        showFlash("error", "Action failed. Check the project logs.");
        return;
      }

      window.location.reload();
    } catch (error) {
      showFlash("error", "Action failed before the dashboard received a response.");
      setSubmitting(form, false);
    }
  }

  document.addEventListener("submit", function (event) {
    var form = event.target.closest("form[data-async-form]");
    if (!form) {
      return;
    }
    event.preventDefault();
    submitInPage(form);
  });
})();
