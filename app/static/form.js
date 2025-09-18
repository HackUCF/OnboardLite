// Other dropdown logic

let dropdowns = document.querySelectorAll("select");
let checkboxes = document.querySelectorAll("fieldset.checkbox");

for (let i = 0; i < dropdowns.length; i++) {
  dropdowns[i].onchange = (evt) => {
    let el = evt.target;
    if (el.value == "_other") {
      el.parentElement.querySelector(".other_dropdown").style.display = "block";
    } else {
      el.parentElement.querySelector(".other_dropdown").style.display = "none";
    }
  };
}

for (let i = 0; i < checkboxes.length; i++) {
  checkboxes[i].onchange = (evt) => {
    let el = evt.target;
    if (el.value == "_other" && el.checked) {
      el.parentElement.parentElement.querySelector(
        ".other_checkbox",
      ).style.display = "block";
    } else if (el.value == "_other") {
      el.parentElement.parentElement.querySelector(
        ".other_checkbox",
      ).style.display = "none";
    }
  };
}

// Custom auto-dismissing banner system.else
function banner(str, trusted) {
  let el = document.createElement("div");

  // Decide if we want to insert HTML or not.
  if (trusted) el.innerHTML = str;
  else el.innerText = str;

  el.classList = "banner_vanishing";
  el.style.opacity = 0;
  document.body.prepend(el);

  window.setTimeout((_) => {
    el.style.opacity = 1;

    window.setTimeout((_) => {
      el.style.opacity = 0;

      window.setTimeout((_) => {
        el.parentElement.removeChild(el);
      }, 250);
    }, 5000);
  }, 150);
}

// Gets the value of an element.
function get_value(el) {
  let key = el.getAttribute("name");
  let value;

  if (el.nodeName == "INPUT") {
    // this is text
    value = el.value;
  } else if (el.nodeName == "SELECT") {
    // this is a dropdown
    if (el.value == "_other") {
      // Take value from Other text box
      value = document.querySelector(
        `.other_dropdown#${key.replaceAll(".", "_").replaceAll(" ", "_")}`,
      ).value;
    } else if (el.value == "_default") {
      value = undefined;
    } else {
      // Get normal value.
      value = el.value;
    }
  } else if (el.nodeName == "FIELDSET") {
    // this is a radio or a checkbox
    value = "";
    let options = el.querySelectorAll("div > input");
    for (let j = 0; j < options.length; j++) {
      if (options[j].checked) {
        if (value != "") value += ", ";

        if (options[j].value == "_other") {
          // Take value from Other text box
          value += document.querySelector(
            `.other_checkbox#${key.replaceAll(".", "_").replaceAll(" ", "_")}`,
          ).value;
        } else {
          value += options[j].value;
        }
      }
    }
  }

  if (value == "") value = undefined;

  return value;
}

// Populate the body for the submission response.
function get_body() {
  // This is the response we are building.
  let body = {};

  // This points to everything we need to build the response.
  const els = document.querySelectorAll(".kennelish_input");

  /*
        General idea I'm thinking: iterate through inputs, identify what we need to do
        to get a valid input (such as checking fieldset children), then add to body object.
     */

  for (let i = 0; i < els.length; i++) {
    let key = els[i].getAttribute("name");
    let value = get_value(els[i]);

    body[key] = value;

    // I am sure we could make this recursive in the future.
    // if (key.indexOf(".") != -1) {
    //     let dot = key.indexOf(".");
    //     let parent = key.substring(0, dot);
    //     let child = key.substring(dot + 1);
    //     body[parent] = {};
    //     body[parent][child] = value;
    // } else {
    // body[key] = value;
    // }
  }

  if (document.querySelector(".signature")) {
    const timestamp = Date.now();
    let sign_key = document.querySelector(".signature").getAttribute("name");

    body[sign_key] = timestamp;
  }

  return body;
}

// NID validation and formatting functions
function isValidNID(nid) {
  // UCF NID format: 2 lowercase letters followed by 6 digits
  const nidPattern = /^([a-z]{2}[0-9]{6})$/;
  return nidPattern.test(nid);
}

function formatNIDValue(value) {
  if (!value) return value;
  // Convert to lowercase and remove any non-alphanumeric characters
  return value.toLowerCase().replace(/[^a-z0-9]/g, '');
}

function getSpecificNIDError(formattedValue) {
  if (!formattedValue) {
    return " (required - format: ab123456)";
  }
  
  if (formattedValue.length < 8) {
    return ` (too short - need ${8 - formattedValue.length} more characters)`;
  }
  
  if (formattedValue.length > 8) {
    return " (too long - should be 8 characters)";
  }
  
  // Check specific pattern issues
  const firstTwoChars = formattedValue.substring(0, 2);
  const lastSixChars = formattedValue.substring(2);
  
  if (!/^[a-z]{2}$/.test(firstTwoChars)) {
    return " (must start with 2 letters)";
  }
  
  if (!/^[0-9]{6}$/.test(lastSixChars)) {
    return " (must end with 6 numbers)";
  }
  
  return " (invalid format - use ab123456)";
}

function validateNIDField(element, is_loud) {
  const value = element.value;
  const formattedValue = formatNIDValue(value);
  
  // Auto-format the field value as the user types
  if (value !== formattedValue) {
    element.value = formattedValue;
  }
  
  const isValid = formattedValue && isValidNID(formattedValue);
  
  if (is_loud) {
    // Clear all previous error messages
    if (element.placeholder) {
      element.placeholder = element.placeholder
        .replaceAll(" (required!)", "")
        .replaceAll(" (invalid format!)", "")
        .replaceAll(/ \(required - format: ab123456\)/, "")
        .replaceAll(/ \(too short - need \d+ more characters?\)/, "")
        .replaceAll(" (too long - should be 8 characters)", "")
        .replaceAll(" (must start with 2 letters)", "")
        .replaceAll(" (must end with 6 numbers)", "")
        .replaceAll(" (invalid format - use ab123456)", "");
    }
    
    if (!isValid) {
      element.style.background = "var(--hackucf-error)";
      element.style.color = "white";
      if (element.placeholder) {
        element.placeholder += getSpecificNIDError(formattedValue);
      }
    } else {
      // Reset styling for valid input
      element.style.background = "var(--hackucf-off-white)";
      element.style.color = "black";
    }
  }
  
  return isValid;
}

function validate_required(is_loud) {
  const els = document.querySelectorAll("[required]");
  let result = true;

  for (let i = 0; i < els.length; i++) {
    let element = els[i];
    
    // Special handling for NID fields
    if (element.nodeName === "INPUT" && element.name === "nid") {
      if (!validateNIDField(element, is_loud)) {
        result = false;
      }
      continue;
    }
    
    let value = get_value(element);
    // Undefined checks
    if (typeof value == "undefined" || !RegExp(element.pattern).test(value)) {
      // is_loud makes us populate 'validation required' texts.
      if (is_loud) {
        if (element.nodeName == "FIELDSET") {
          element.style.color = "var(--hackucf-error)";
          element.style.fontWeight = "bold";
        } else {
          element.style.background = "var(--hackucf-error)";
          element.style.color = "white";
          if (element.placeholder) {
            element.placeholder = element.placeholder.replaceAll(
              " (required!)",
              "",
            );
            element.placeholder += " (required!)";
          }
        }
      }
      result = false;
    } else if (is_loud) {
      // Revert previous style changes if input filled out.
      if (element.nodeName == "FIELDSET") {
        element.style.color = "var(--text)";
        element.style.fontWeight = "normal";
      } else {
        element.style.background = "var(--hackucf-off-white)";
        element.style.color = "black";
        if (element.placeholder) {
          element.placeholder = element.placeholder.replaceAll(
            " (required!)",
            "",
          );
        }
      }
    }
  }

  if (!result && is_loud) banner("Required fields missing!");

  return result;
}

// Submits data to the API, then goes to the given page.
function submit_and_nav(target_url) {
  const path = window.location.pathname;
  const second_slash = path.indexOf("/", 2) + 1;
  const third_slash = path.indexOf("/", second_slash);
  const form_id = path.substring(second_slash, third_slash);

  const did_we_do_required = validate_required(true);

  if (!did_we_do_required) {
    return;
  }

  let body = get_body();

  fetch(`/api/form/${form_id}`, {
    method: "POST",
    mode: "same-origin",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  })
    .then((response) => {
      if (!response.ok) {
        return response.json().then((errorData) => {
          console.error("Error data:", errorData); // Debugging line
          banner(errorData.detail);
          throw new Error(errorData.message || "An error occurred");
        });
      }
      return response;
    })
    .then(() => {
      window.location.href = target_url;
    });
}

function nav_to(target_url) {
  window.location.href = target_url;
}

function resetInfra() {
  var confirmation = confirm(
    "Are you sure you want to delete your account? If you just need a password reset create a thread in #infra-helpdesk on Discord. THIS WILL DELETE ALL THE DATA ASSOCIATED WITH YOUR ACCOUNT.",
  );
  if (!confirmation) {
    // If the user clicked Cancel, stop the function
    return;
  }
  fetch("/infra/reset")
    .then((response) => {
      if (response.status === 429) {
        alert(
          "You have reset your account this week already. If this is in error or you need more support create a thread in #infra-helpdesk on Discord.",
        );
        return;
      }
      return response.json();
    })
    .then((data) => {
      if (data) {
        const { username, password } = data;
        alert(`
                You have reset your infra credentials. These should have been emailed to you. If you did not receive an email, please create a thread in #infra-helpdesk on Discord.\n
                Username: ${username}\n
                Password: ${password}`);
      }
    });
}

function downloadProfile() {
  const downloadEndpoint = "/infra/OpenVPN";
  const anchor = document.createElement("a");
  anchor.href = downloadEndpoint;
  anchor.download = "HackUCF.ovpn";
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
}
function provisionInfra() {
  fetch("/infra/provision")
    .then((data) => {
      return data.json();
    })
    .then((resp) => {
      window.location.href = "https://horizon.hackucf.org/";
    });
}

function logoff() {
  document.cookie = "token=; Max-Age=0; path=/; domain=" + location.hostname;
  window.location.href = "/logout";
}

window.onload = (evt) => {
  if (document.getElementById("resetInfra")) {
    document.getElementById("resetInfra").onclick = (evt) => {
      document.getElementById("resetInfra").disabled = true;
      resetInfra();
    };
  }

  if (
    typeof QRCodeStyling !== "undefined" &&
    document.getElementById("membership_id")
  ) {
    const qrCode = new QRCodeStyling({
      width: 260,
      height: 260,
      type: "svg",
      data: document.getElementById("membership_id").innerText,
      image: "/static/qr_hack_light.svg",
      dotsOptions: {
        color: "#000",
      },
      backgroundOptions: {
        color: "#fff",
      },
      imageOptions: {
        crossOrigin: "anonymous",
        margin: 5,
        imageSize: 0.5,
      },
    });
    qrCode.append(document.getElementById("qr"));
  }

  // This variable is licensed CC BY-SA. Just this variable.
  // https://stackoverflow.com/a/9039885
  const is_iOS =
    [
      "iPad Simulator",
      "iPhone Simulator",
      "iPod Simulator",
      "iPad",
      "iPhone",
      "iPod",
    ].includes(navigator.platform) ||
    (navigator.userAgent.includes("Mac") && "ontouchend" in document);

  if (is_iOS && document.getElementById("apple_wallet")) {
    document.getElementById("apple_wallet").style.display = "block";
  }

  // Add real-time validation for NID fields
  const nidInputs = document.querySelectorAll('input[name="nid"]');
  nidInputs.forEach(function(nidInput) {
    nidInput.addEventListener('input', function(event) {
      const formatted = formatNIDValue(event.target.value);
      if (event.target.value !== formatted) {
        event.target.value = formatted;
      }
      
      // Real-time validation feedback with specific error messages
      if (formatted.length > 0) {
        if (isValidNID(formatted)) {
          event.target.style.background = "var(--hackucf-off-white)";
          event.target.style.color = "black";
          // Clear any error messages from placeholder
          if (event.target.placeholder) {
            event.target.placeholder = event.target.placeholder
              .replaceAll(/ \(required - format: ab123456\)/, "")
              .replaceAll(/ \(too short - need \d+ more characters?\)/, "")
              .replaceAll(" (too long - should be 8 characters)", "")
              .replaceAll(" (must start with 2 letters)", "")
              .replaceAll(" (must end with 6 numbers)", "")
              .replaceAll(" (invalid format - use ab123456)", "");
          }
        } else {
          // Show gentle feedback while typing, more specific on blur
          event.target.style.background = "#ffeeee";
          event.target.style.color = "black";
        }
      }
    });
    
    nidInput.addEventListener('blur', function(event) {
      // Validate on blur (when user leaves the field) with specific error messages
      validateNIDField(event.target, true);
    });
  });

  // Infra checker
  fetch("https://horizon.hackucf.org", { mode: "no-cors" })
    .then((evt) => {
      // Do stuff if on Infra
      document.querySelector(".infra_modal").style.display = "block";
    })
    .catch((evt) => {
      // Do stuff if not on Infra
    });
};
