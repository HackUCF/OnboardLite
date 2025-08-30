// SPDX-License-Identifier: MIT
// Copyright (c) 2024 Collegiate Cyber Defense Club

let userDict = {};
let userList;
let qrScanner;

function load() {
  let valueNames = [
    "Name",
    "Status",
    "NID",
    "Discord",
    "Email",
    "Experience",
    "Major",
    "Details",
  ];
  let valueItems = "<tr>";
  let valueHeader = "<tr>";
  for (let i = 0; i < valueNames.length; i++) {
    valueItems += `<td class="${valueNames[i].toLowerCase()}"></td>`;
    valueHeader += `<td><button class="sort totally_text" data-sort="${valueNames[i].toLowerCase()}">${valueNames[i]}</button></td>`;
    valueNames[i] = valueNames[i].toLowerCase();
  }
  valueItems += "</tr>";
  valueHeader += "</tr>";

  document.querySelector("thead").innerHTML = valueHeader;

  const options = {
    valueNames: valueNames,
    item: valueItems,
    searchColumns: ["name", "nid", "discord", "email", "major", "status"],
  };

  let members = [];
  let count_full_member = 0;
  let count_all = 0;

  fetch("/admin/list")
    .then((data) => {
      return data.json();
    })
    .then((data2) => {
      data2 = data2.data;
      for (let i = 0; i < data2.length; i++) {
        member = data2[i];

        let userStatus = userStatusString(member);
        let userEntry = {
          id: sanitizeHTML(member.id).replaceAll("&#45;", "-"),
          name: sanitizeHTML(member.first_name + " " + member.surname),
          status: userStatus,
          discord: "@" + sanitizeHTML(member.discord.username),
          email: sanitizeHTML(member.email),
          nid: sanitizeHTML(member.nid),
          experience: sanitizeHTML(member.experience),
          major: sanitizeHTML(member.major),
          details: `<button class="searchbtn btn" onclick="showUser('${sickoModeSanitize(member.id)}')">Details</a>`,
          is_full_member: Boolean(member.is_full_member),
        };

        count_all++;
        if (member.is_full_member) count_full_member++;

        members.push(userEntry);

        member.name = member.first_name + " " + member.surname;
        member.username = "@" + member.discord.username;
        member.pfp = member.discord.avatar;
        member.status = userStatus;
        userDict[sickoModeSanitize(member.id)] = member;
      }

      userList = new List("users", options, members);

      document.querySelector(".right").innerHTML +=
        `<br>${count_full_member} dues-paying, ${count_all} total`;
    });
}

function userStatusString(member) {
  if (member.sudo) return "Administrator";

  //if (member.cyberlab_monitor.signtime !== 0)
  //    return "CyberLab Monitor";

  if (member.ops_email) return "Operations Member";

  if (member.is_full_member) return "Dues-Paying Member";

  if (!member.did_pay_dues) return "Needs Dues Payment";

  if (!member.ethics_form.signtime !== 0) return "Needs Ethics Form";

  return "Attendee"; // Unactivated account
}

// Sanitizes any non-alphanum.
function sickoModeSanitize(val) {
  return val.replaceAll(/[^\w\-]/g, "");
}

/**
 * Sanitize and encode all HTML in a user-submitted string
 * https://portswigger.net/web-security/cross-site-scripting/preventing
 * Needed because our table-searching library is circumstantially vulnerable to XSS.
 * @param  {String} str  The user-submitted string
 * @return {String} str  The sanitized string
 */
const sanitizeHTML = (data) => {
  if (data) {
    data = data.toString();
    return data.replace(/[^\w. ]/gi, function (c) {
      return "&#" + c.charCodeAt(0) + ";";
    });
  } else {
    return "";
  }
};

function showTable() {
  qrScanner.stop();

  document.getElementById("user").style.display = "none";
  document.getElementById("scanner").style.display = "none";
  document.getElementById("users").style.display = "block";
}

function showQR() {
  qrScanner.start();

  const camLS = localStorage.getItem("adminCam");
  if (camLS && typeof camLS !== "undefined") {
    qrScanner.setCamera(camLS);
  }

  document.getElementById("user").style.display = "none";
  document.getElementById("users").style.display = "none";
  document.getElementById("scanner").style.display = "block";
}

function showUser(userId) {
  const user = userDict[userId];

  // Header details
  document.getElementById("pfp").src = user.pfp;
  document.getElementById("name").innerText = user.name;
  document.getElementById("discord").innerText = user.username;

  // Statuses
  document.getElementById("statusColor").style.color = user.is_full_member
    ? "#51cd7f"
    : "#cf565f";

  document.getElementById("status").innerText = user.status;
  document.getElementById("did_pay_dues").innerText = user.did_pay_dues
    ? "✔️"
    : "❌";
  document.getElementById("ethics_form").innerText =
    user.ethics_form.signtime &&
    Number.parseInt(user.ethics_form.signtime) !== -1
      ? new Date(Number.parseInt(user.ethics_form.signtime)).toLocaleString()
      : "❌";
  document.getElementById("is_full_member").innerText = user.is_full_member
    ? "✔️"
    : "❌";
  document.getElementById("shirt_status").innerText = user.did_get_shirt
    ? "Claimed"
    : `Unclaimed: Size ${user.shirt_size}`;

  // Identifiers
  document.getElementById("id").innerText = user.id;
  document.getElementById("nid").innerText = user.nid;
  document.getElementById("ucfid").innerText = user.ucfid
    ? user.ucfid
    : "(unknown)";
  document.getElementById("email").innerText = user.email;
  document.getElementById("minecraft").innerText = user.minecraft
    ? user.minecraft
    : "Not Provided";
  document.getElementById("github").innerText = user.github
    ? user.github
    : "Not Provided";
  document.getElementById("phone_number").innerText = user.phone_number
    ? user.phone_number
    : "Not Provided";

  // Demography
  document.getElementById("class_standing").innerText = user.class_standing;
  document.getElementById("experience").innerText = user.experience;
  document.getElementById("attending").innerText = user.attending
    ? user.attending
    : "(none)";
  document.getElementById("curiosity").innerText = user.curiosity
    ? user.curiosity
    : "(none)";
  document.getElementById("major").innerText = user.major
    ? user.major
    : "(unknown)";
  document.getElementById("gender").innerText = user.gender
    ? user.gender
    : "(unknown)";
  document.getElementById("c3_interest").innerText = user.c3_interest
    ? "✔️"
    : "❌";
  document.getElementById("is_returning").innerText = user.is_returning
    ? "✔️"
    : "❌";
  document.getElementById("comments").innerText = user.comments
    ? user.comments
    : "(none)";

  document.getElementById("user_json").innerText = JSON.stringify(
    user,
    "\t",
    "\t",
  );

  // Load membership history
  loadMembershipHistory(userId);

  // Set buttons up
  document.getElementById("payDues").onclick = (evt) => {
    if (window.confirm("Are you sure you want to mark this user as paid?")) {
      editUser({
        id: user.id,
        did_pay_dues: true,
      });
    }
    setTimeout((evt) => {
      verifyUser(user.id);
    }, 2000);
  };
  document.getElementById("payDues").style.display = user.did_pay_dues
    ? "none"
    : "inline-block";

  document.getElementById("reverify").onclick = (evt) => {
    verifyUser(user.id);
  };
  document.getElementById("reverify").style.display = user.is_full_member
    ? "none"
    : "inline-block";

  document.getElementById("claimShirt").onclick = (evt) => {
    editUser({
      id: user.id,
      did_get_shirt: true,
    });
  };
  document.getElementById("claimShirt").style.display = user.did_get_shirt
    ? "none"
    : "inline-block";

  document.getElementById("setAdmin").onclick = (evt) => {
    if (window.confirm("Make User Admin?")) {
      editUser({
        id: user.id,
        sudo: !user.sudo,
      });
    }
  };
  document.getElementById("adminLabel").innerText = user.sudo
    ? "Revoke Admin"
    : "Promote to Admin";

  document.getElementById("joinInfra").onclick = (evt) => {
    inviteToInfra(user.id, false);
  };

  document.getElementById("infraReset").onclick = (evt) => {
    inviteToInfra(user.id, true);
  };
  document.getElementById("infraLabel").innerText = user.infra_email
    ? "Reset Infra Account"
    : "Invite to Infra";

  document.getElementById("sendMessage").onclick = (evt) => {
    const message = prompt("Please enter message to send to user:");
    sendDiscordDM(user.id, message);
  };

  document.getElementById("migrateDiscord").onclick = (evt) => {
    openDiscordMigration(user.id);
  };

  // Set page visibilities
  document.getElementById("users").style.display = "none";
  document.getElementById("scanner").style.display = "none";
  document.getElementById("user").style.display = "block";
}

function editUser(payload) {
  const options = {
    method: "POST",
    body: JSON.stringify(payload),
    headers: {
      "Content-Type": "application/json",
    },
  };
  const user_id = payload.id;
  fetch("/admin/get", options);

  fetch("/admin/get?member_id=" + payload.id)
    .then((data) => {
      return data.json();
    })
    .then((data2) => {
      // Update user data.
      let member = data2.data;

      member.name = member.first_name + " " + member.surname;
      member.username = "@" + member.discord.username;
      member.pfp = member.discord.avatar;
      member.status = userStatusString(member);

      userDict[user_id] = member;
      showUser(user_id);
    });
}

function sendDiscordDM(user_id, message) {
  const payload = {
    msg: message,
  };
  const options = {
    method: "POST",
    body: JSON.stringify(payload),
    headers: {
      "Content-Type": "application/json",
    },
  };
  fetch("/admin/message?member_id=" + user_id, options)
    .then((data) => {
      return data.json();
    })
    .then((data2) => {
      alert(data2.msg);
    });
}

function verifyUser(user_id) {
  fetch("/admin/refresh?member_id=" + user_id)
    .then((data) => {
      return data.json();
    })
    .then((data2) => {
      // Update user data.
      let member = data2.data;

      member.name = member.first_name + " " + member.surname;
      member.username = "@" + member.discord.username;
      member.pfp = member.discord.avatar;
      member.status = userStatusString(member);

      userDict[user_id] = member;
      showUser(user_id);
    });
}

function inviteToInfra(user_id, reset_password = false) {
  fetch(
    "/admin/infra?member_id=" + user_id + "&reset_password=" + reset_password,
  )
    .then((data) => {
      return data.json();
    })
    .then((resp) => {
      // Update user data.
      alert(`The user has been provisioned and a Discord message with credentials sent!

Username: ${resp.username}
Password: ${resp.password}`);

      userDict[user_id].infra_email = resp.username;
      showUser(user_id);
    });
}

function loadMembershipHistory(userId) {
  const historyContainer = document.getElementById("membership_history");
  historyContainer.innerHTML = "<p>Loading membership history...</p>";

  fetch(`/admin/membership_history/?user_id=${userId}`)
    .then((response) => response.json())
    .then((data) => {
      if (data.error) {
        historyContainer.innerHTML = `<p>Error loading history: ${data.error}</p>`;
        return;
      }

      const history = data.data;
      if (history.length === 0) {
        historyContainer.innerHTML =
          "<p>No membership history found for this user.</p>";
        return;
      }

      let historyHTML = "<table class='data_table'>";
      historyHTML += "<thead><tr>";
      historyHTML += "<th>Reset Date</th>";
      historyHTML += "<th>Was Member</th>";
      historyHTML += "<th>Paid Dues</th>";
      historyHTML += "<th>Reason</th>";
      historyHTML += "<th>Name at Reset</th>";
      historyHTML += "<th>Email at Reset</th>";
      historyHTML += "<th>Discord at Reset</th>";
      historyHTML += "</tr></thead><tbody>";

      history.forEach((record) => {
        const resetDate = new Date(record.reset_date).toLocaleString();
        const fullName = `${record.first_name_snapshot} ${record.surname_snapshot}`;

        historyHTML += "<tr>";
        historyHTML += `<td>${resetDate}</td>`;
        historyHTML += `<td>${record.was_full_member ? "✔️" : "❌"}</td>`;
        historyHTML += `<td>${record.had_paid_dues ? "✔️" : "❌"}</td>`;
        historyHTML += `<td>${sanitizeHTML(record.reset_reason)}</td>`;
        historyHTML += `<td>${sanitizeHTML(fullName)}</td>`;
        historyHTML += `<td>${sanitizeHTML(record.email_snapshot || "N/A")}</td>`;
        historyHTML += `<td>${sanitizeHTML(record.discord_username_snapshot || "N/A")}</td>`;
        historyHTML += "</tr>";
      });

      historyHTML += "</tbody></table>";
      historyContainer.innerHTML = historyHTML;
    })
    .catch((error) => {
      console.error("Error loading membership history:", error);
      historyContainer.innerHTML = "<p>Error loading membership history.</p>";
    });
}

function logoff() {
  document.cookie = "token=; Max-Age=0; path=/; domain=" + location.hostname;
  window.location.href = "/logout";
}

function changeCamera() {
  QrScanner.listCameras().then((evt) => {
    const cameras = evt;
    let camArray = [];
    let camString = "Please enter a camera number:";
    for (let i = 0; i < cameras.length; i++) {
      camString += `\n${i}: ${cameras[i].label}`;
      camArray.push(cameras[i].id);
    }
    let camSelect = prompt(camString);

    localStorage.setItem("adminCam", camArray[camSelect]);
    qrScanner.setCamera(camArray[camSelect]);
  });
}

function scannedCode(result) {
  // Enter load mode...
  qrScanner.stop();

  showUser(result.data);
}

function filter(showOnlyActiveUsers) {
  // showActiveUsers == true -> only active shown
  // showActiveUsers == false -> only inactive shown
  userList.filter((item) => {
    let activeOrInactive = item.values().is_full_member;
    if (!showOnlyActiveUsers) {
      activeOrInactive = !activeOrInactive;
    }
    return activeOrInactive;
  });

  document.getElementById("activeFilter").innerText = showOnlyActiveUsers
    ? "Active"
    : "Inactive";
  document.getElementById("activeFilter").onclick = (evt) => {
    filter(!showOnlyActiveUsers);
  };
}

window.onload = (evt) => {
  load();

  // Prep QR library
  const videoElem = document.querySelector("video");
  qrScanner = new QrScanner(videoElem, scannedCode, {
    maxScansPerSecond: 10,
    highlightScanRegion: true,
    returnDetailedScanResult: true,
  });

  // Default behavior
  document.getElementById("goBackBtn").onclick = (evt) => {
    showTable();
  };

  // Turn ON the QR Scanner mode.
  document.getElementById("scannerOn").onclick = (evt) => {
    showQR();

    document.getElementById("goBackBtn").onclick = (evt) => {
      showQR();
    };
  };

  document.getElementById("scannerOff").onclick = (evt) => {
    showTable();

    document.getElementById("goBackBtn").onclick = (evt) => {
      showTable();
    };
  };

  document.getElementById("changeCamera").onclick = (evt) => {
    changeCamera();
  };

  // Filter buttons
  document.getElementById("activeFilter").onclick = (evt) => {
    filter(true);
  };
};

// Discord Migration Functions
function openDiscordMigration(userId) {
  document.getElementById("migrationModal").style.display = "block";
  document.getElementById("migrationUserId").value = userId;
  document.getElementById("migrationResults").innerHTML = "";
  document.getElementById("migrationSubmit").disabled = true;
  document.getElementById("newDiscordId").value = "";
  document.getElementById("identityVerified").checked = false;
}

function closeMigrationModal() {
  document.getElementById("migrationModal").style.display = "none";
}

async function checkDiscordAccount() {
  const discordId = document.getElementById("newDiscordId").value;
  const resultsDiv = document.getElementById("migrationResults");

  if (!discordId) {
    alert("Please enter a Discord ID");
    return;
  }

  // Validate Discord ID format
  if (!/^[0-9]{17,20}$/.test(discordId)) {
    resultsDiv.innerHTML = `
      <div class="error">Invalid Discord ID format. Must be 17-20 digits.</div>
    `;
    document.getElementById("migrationSubmit").disabled = true;
    return;
  }

  try {
    const response = await fetch(
      `/admin/get_by_snowflake/?discord_id=${discordId}`,
    );

    if (response.ok) {
      const data = await response.json();
      const user = data.data;

      resultsDiv.innerHTML = `
        <div class="account-found">
          <h4>✅ Account Found</h4>
          <p><strong>Discord Username:</strong> ${user.discord?.username || "Unknown"}</p>
          <p><strong>Name:</strong> ${user.first_name || "Not set"} ${user.surname || ""}</p>
          <p><strong>Email:</strong> ${user.email || "Not set"}</p>
          <p><strong>Is Member:</strong> ${user.is_full_member ? "Yes" : "No"}</p>
          <p><strong>Join Date:</strong> ${user.join_date || "Not set"}</p>
          ${
            !user.first_name || !user.surname || !user.email
              ? '<p class="warning">⚠️ This appears to be a new/temporary account with minimal data</p>'
              : '<p class="warning">⚠️ This account has significant data that will be lost</p>'
          }
        </div>
      `;

      // Enable migration button
      document.getElementById("migrationSubmit").disabled = false;
    } else {
      resultsDiv.innerHTML = `
        <div class="account-not-found">
          <h4>❌ No Account Found</h4>
          <p>No user account exists with Discord ID: ${discordId}</p>
          <p>The user must create an account with this Discord ID first.</p>
        </div>
      `;

      // Disable migration button
      document.getElementById("migrationSubmit").disabled = true;
    }
  } catch (error) {
    resultsDiv.innerHTML = `<div class="error">Error checking account: ${error.message}</div>`;
    document.getElementById("migrationSubmit").disabled = true;
  }
}

// Add event listener for migration form
document.addEventListener("DOMContentLoaded", function () {
  const migrationForm = document.getElementById("migrationForm");
  if (migrationForm) {
    migrationForm.addEventListener("submit", async function (e) {
      e.preventDefault();

      const formData = new FormData(e.target);
      const data = {
        old_user_id: formData.get("user_id"),
        new_discord_id: formData.get("new_discord_id"),
        identity_verified: document.getElementById("identityVerified").checked,
      };

      if (!data.identity_verified) {
        alert("You must verify the user's identity before proceeding");
        return;
      }

      if (
        !confirm(
          "Are you sure you want to execute this migration? This action cannot be undone.",
        )
      ) {
        return;
      }

      try {
        const response = await fetch("/admin/migrate_discord_account/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        });

        const result = await response.json();

        if (response.ok && result.success) {
          document.getElementById("migrationResults").innerHTML = `
            <div class="success">
              <h4>✅ Migration Successful</h4>
              <p>${result.message}</p>
              <p><strong>Old Discord ID:</strong> ${result.old_discord_id}</p>
              <p><strong>New Discord ID:</strong> ${result.new_discord_id}</p>
              <p><strong>New Username:</strong> ${result.new_discord_username}</p>
            </div>
          `;

          // Refresh the user data after a delay
          setTimeout(() => {
            closeMigrationModal();
            showUser(data.old_user_id);
          }, 3000);
        } else {
          throw new Error(
            result.detail || result.message || "Migration failed",
          );
        }
      } catch (error) {
        document.getElementById("migrationResults").innerHTML =
          `<div class="error">Migration failed: ${error.message}</div>`;
      }
    });
  }
});
