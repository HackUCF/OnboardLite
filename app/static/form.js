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

function validate_required(is_loud) {
  const els = document.querySelectorAll("[required]");
  let result = true;

  for (let i = 0; i < els.length; i++) {
    let value = get_value(els[i]);
    // Undefined checks
    if (typeof value == "undefined" || !RegExp(els[i].pattern).test(value)) {
      // is_loud makes us populate 'validation required' texts.
      if (is_loud) {
        if (els[i].nodeName == "FIELDSET") {
          els[i].style.color = "var(--hackucf-error)";
          els[i].style.fontWeight = "bold";
        } else {
          els[i].style.background = "var(--hackucf-error)";
          els[i].style.color = "white";
          if (els[i].placeholder) {
            els[i].placeholder = els[i].placeholder.replaceAll(
              " (required!)",
              "",
            );
            els[i].placeholder += " (required!)";
          }
        }
      }
      result = false;
    } else if (is_loud) {
      // Revert previous style changes if input filled out.
      if (els[i].nodeName == "FIELDSET") {
        els[i].style.color = "var(--text)";
        els[i].style.fontWeight = "normal";
      } else {
        els[i].style.background = "var(--hackucf-off-white)";
        els[i].style.color = "black";
        if (els[i].placeholder) {
          els[i].placeholder = els[i].placeholder.replaceAll(
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
