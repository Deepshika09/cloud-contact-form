(function () {
  const NAME_MIN = 2;
  const NAME_MAX = 80;
  const MESSAGE_MIN = 10;
  const MESSAGE_MAX = 2000;
  const EMAIL_MAX = 254;
  const NAME_RE = /^[A-Za-z][A-Za-z '\-]*$/;
  const EMAIL_RE = /^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,24}$/;
  const REQUEST_TIMEOUT_MS = 12000;

  const form = document.getElementById("form");
  const banner = document.getElementById("banner");
  const submit = document.getElementById("submit");
  const counter = document.getElementById("counter");
  const messageEl = document.getElementById("message");

  const fields = {
    name: document.getElementById("name"),
    email: document.getElementById("email"),
    message: messageEl,
  };

  function apiUrl() {
    const url = window.APP_CONFIG && window.APP_CONFIG.apiUrl;
    if (!url || url.indexOf("REPLACE_WITH") !== -1) {
      return "";
    }
    return url;
  }

  function setBanner(kind, text) {
    banner.hidden = !text;
    banner.className = "banner" + (kind ? " " + kind : "");
    banner.textContent = text || "";
  }

  function setFieldError(name, message) {
    const input = fields[name];
    const error = document.getElementById(name + "-error");
    if (!input || !error) return;
    if (message) {
      input.classList.add("invalid");
      input.setAttribute("aria-invalid", "true");
      error.hidden = false;
      error.textContent = message;
    } else {
      input.classList.remove("invalid");
      input.removeAttribute("aria-invalid");
      error.hidden = true;
      error.textContent = "";
    }
  }

  function clearErrors() {
    Object.keys(fields).forEach(function (name) {
      setFieldError(name, "");
    });
  }

  function validateClient(values) {
    const errors = {};
    const name = values.name.trim().replace(/\s+/g, " ");
    const email = values.email.trim().toLowerCase();
    const message = values.message.trim();

    if (!name) errors.name = "Name is required.";
    else if (name.length < NAME_MIN || name.length > NAME_MAX)
      errors.name = "Name must be between " + NAME_MIN + " and " + NAME_MAX + " characters.";
    else if (!NAME_RE.test(name))
      errors.name = "Use letters, spaces, hyphens, or apostrophes only.";

    if (!email) errors.email = "Email is required.";
    else if (email.length > EMAIL_MAX) errors.email = "Email is too long.";
    else if (!EMAIL_RE.test(email)) errors.email = "Enter a valid email address.";

    if (!message) errors.message = "Message is required.";
    else if (message.length < MESSAGE_MIN || message.length > MESSAGE_MAX)
      errors.message =
        "Message must be between " + MESSAGE_MIN + " and " + MESSAGE_MAX + " characters.";

    return { errors: errors, payload: { name: name, email: email, message: message } };
  }

  function setLoading(isLoading) {
    submit.disabled = isLoading;
    submit.classList.toggle("loading", isLoading);
    submit.setAttribute("aria-busy", isLoading ? "true" : "false");
  }

  function updateCounter() {
    counter.textContent = messageEl.value.length + " / " + MESSAGE_MAX;
  }

  Object.keys(fields).forEach(function (name) {
    fields[name].addEventListener("input", function () {
      setFieldError(name, "");
      if (name === "message") updateCounter();
    });
  });

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    setBanner("", "");
    clearErrors();

    const result = validateClient({
      name: fields.name.value,
      email: fields.email.value,
      message: fields.message.value,
    });

    const errorNames = Object.keys(result.errors);
    if (errorNames.length) {
      errorNames.forEach(function (name) {
        setFieldError(name, result.errors[name]);
      });
      setBanner("fail", "Please fix the highlighted fields.");
      fields[errorNames[0]].focus();
      return;
    }

    const url = apiUrl();
    if (!url) {
      setBanner(
        "fail",
        "API URL is not configured. Copy frontend/config.example.js to config.js and set apiUrl."
      );
      return;
    }

    const controller = new AbortController();
    const timer = setTimeout(function () {
      controller.abort();
    }, REQUEST_TIMEOUT_MS);

    setLoading(true);

    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(result.payload),
      signal: controller.signal,
    })
      .then(function (response) {
        return response
          .json()
          .catch(function () {
            return {};
          })
          .then(function (body) {
            return { response: response, body: body };
          });
      })
      .then(function (resultHttp) {
        const response = resultHttp.response;
        const body = resultHttp.body || {};

        if (response.ok && body.ok) {
          setBanner("success", body.message || "Thanks - your message was received.");
          form.reset();
          updateCounter();
          return;
        }

        if (body.fields) {
          Object.keys(body.fields).forEach(function (name) {
            setFieldError(name, body.fields[name]);
          });
        }

        setBanner("fail", body.error || "Something went wrong. Please try again.");
      })
      .catch(function (error) {
        if (error && error.name === "AbortError") {
          setBanner("fail", "The request timed out. Check your connection and try again.");
          return;
        }
        setBanner(
          "fail",
          "Could not reach the API. Confirm the local server is running, or that API Gateway is deployed and CORS matches this origin."
        );
      })
      .finally(function () {
        clearTimeout(timer);
        setLoading(false);
      });
  });

  updateCounter();
})();
