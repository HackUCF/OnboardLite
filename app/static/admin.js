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
  fetch("/admin/refresh?member_id=" + user_id, {
    method: "POST",
    credentials: "include",
  })
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
  fetch("/admin/infra", {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      member_id: user_id,
      reset_password: reset_password,
    }),
  })
    .then((response) => {
      if (!response.ok) {
        return response.json().then((err) => {
          throw new Error(err.detail || `HTTP ${response.status}`);
        });
      }
      return response.json();
    })
    .then((resp) => {
      alert(`The user has been provisioned and a Discord message with credentials sent!

 Username: ${resp.username}
 Password: ${resp.password}`);

      userDict[user_id].infra_email = resp.username;
      showUser(user_id);
    })
    .catch((error) => {
      alert(`Error provisioning infrastructure access: ${error.message}`);
      console.error("Infra provisioning failed:", error);
    });
}

function loadMembershipHistory(userId) {
  const historyContainer = document.getElementById("membership_history");

  // Show loading message
  const loadingP = document.createElement('p');
  loadingP.textContent = 'Loading membership history...';
  historyContainer.innerHTML = '';
  historyContainer.appendChild(loadingP);

  fetch(`/admin/membership_history/?user_id=${userId}`)
    .then((response) => response.json())
    .then((data) => {
      // Clear loading message
      historyContainer.innerHTML = '';

      if (data.error) {
        const errorP = document.createElement('p');
        errorP.textContent = 'Error loading history: ' + data.error;
        historyContainer.appendChild(errorP);
        return;
      }

      const history = data.data;
      if (history.length === 0) {
        const noHistoryP = document.createElement('p');
        noHistoryP.textContent = 'No membership history found for this user.';
        historyContainer.appendChild(noHistoryP);
        return;
      }

      // Create table
      const table = document.createElement('table');
      table.className = 'data_table';

      // Create thead
      const thead = document.createElement('thead');
      const headerRow = document.createElement('tr');

      const headers = ['Reset Date', 'Was Member', 'Paid Dues', 'Reason', 'Name at Reset', 'Email at Reset', 'Discord at Reset'];
      headers.forEach(headerText => {
        const th = document.createElement('th');
        th.textContent = headerText;
        headerRow.appendChild(th);
      });

      thead.appendChild(headerRow);
      table.appendChild(thead);

      // Create tbody
      const tbody = document.createElement('tbody');

      history.forEach((record) => {
        const row = document.createElement('tr');

        // Reset Date
        const dateCell = document.createElement('td');
        dateCell.textContent = new Date(record.reset_date).toLocaleString();
        row.appendChild(dateCell);

        // Was Member
        const memberCell = document.createElement('td');
        memberCell.textContent = record.was_full_member ? "✔️" : "❌";
        row.appendChild(memberCell);

        // Paid Dues
        const duesCell = document.createElement('td');
        duesCell.textContent = record.had_paid_dues ? "✔️" : "❌";
        row.appendChild(duesCell);

        // Reason
        const reasonCell = document.createElement('td');
        reasonCell.textContent = record.reset_reason;
        row.appendChild(reasonCell);

        // Name at Reset
        const nameCell = document.createElement('td');
        nameCell.textContent = `${record.first_name_snapshot} ${record.surname_snapshot}`;
        row.appendChild(nameCell);

        // Email at Reset
        const emailCell = document.createElement('td');
        emailCell.textContent = record.email_snapshot || "N/A";
        row.appendChild(emailCell);

        // Discord at Reset
        const discordCell = document.createElement('td');
        discordCell.textContent = record.discord_username_snapshot || "N/A";
        row.appendChild(discordCell);

        tbody.appendChild(row);
      });

      table.appendChild(tbody);
      historyContainer.appendChild(table);
    })
    .catch((error) => {
      console.error("Error loading membership history:", error);
      historyContainer.innerHTML = '';
      const errorP = document.createElement('p');
      errorP.textContent = 'Error loading membership history.';
      historyContainer.appendChild(errorP);
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
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error';
    errorDiv.textContent = 'Invalid Discord ID format. Must be 17-20 digits.';
    resultsDiv.innerHTML = '';
    resultsDiv.appendChild(errorDiv);
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

      // Create account found div
      const accountDiv = document.createElement('div');
      accountDiv.className = 'account-found';

      // Create and append header
      const header = document.createElement('h4');
      header.textContent = '✅ Account Found';
      accountDiv.appendChild(header);

      // Discord Username
      const discordP = document.createElement('p');
      const discordStrong = document.createElement('strong');
      discordStrong.textContent = 'Discord Username:';
      discordP.appendChild(discordStrong);
      discordP.appendChild(document.createTextNode(' ' + (user.discord?.username || "Unknown")));
      accountDiv.appendChild(discordP);

      // Name
      const nameP = document.createElement('p');
      const nameStrong = document.createElement('strong');
      nameStrong.textContent = 'Name:';
      nameP.appendChild(nameStrong);
      nameP.appendChild(document.createTextNode(' ' + (user.first_name || "Not set") + ' ' + (user.surname || "")));
      accountDiv.appendChild(nameP);

      // Email
      const emailP = document.createElement('p');
      const emailStrong = document.createElement('strong');
      emailStrong.textContent = 'Email:';
      emailP.appendChild(emailStrong);
      emailP.appendChild(document.createTextNode(' ' + (user.email || "Not set")));
      accountDiv.appendChild(emailP);

      // Is Member
      const memberP = document.createElement('p');
      const memberStrong = document.createElement('strong');
      memberStrong.textContent = 'Is Member:';
      memberP.appendChild(memberStrong);
      memberP.appendChild(document.createTextNode(' ' + (user.is_full_member ? "Yes" : "No")));
      accountDiv.appendChild(memberP);

      // Join Date
      const joinP = document.createElement('p');
      const joinStrong = document.createElement('strong');
      joinStrong.textContent = 'Join Date:';
      joinP.appendChild(joinStrong);
      joinP.appendChild(document.createTextNode(' ' + (user.join_date || "Not set")));
      accountDiv.appendChild(joinP);

      // Warning message
      const warningP = document.createElement('p');
      warningP.className = 'warning';
      if (!user.first_name || !user.surname || !user.email) {
        warningP.textContent = '⚠️ This appears to be a new/temporary account with minimal data';
      } else {
        warningP.textContent = '⚠️ This account has significant data that will be lost';
      }
      accountDiv.appendChild(warningP);

      // Clear and append
      resultsDiv.innerHTML = '';
      resultsDiv.appendChild(accountDiv);

      // Enable migration button
      document.getElementById("migrationSubmit").disabled = false;
    } else {
      // Create account not found div
      const notFoundDiv = document.createElement('div');
      notFoundDiv.className = 'account-not-found';

      const header = document.createElement('h4');
      header.textContent = '❌ No Account Found';
      notFoundDiv.appendChild(header);

      const p1 = document.createElement('p');
      p1.textContent = 'No user account exists with Discord ID: ' + discordId;
      notFoundDiv.appendChild(p1);

      const p2 = document.createElement('p');
      p2.textContent = 'The user must create an account with this Discord ID first.';
      notFoundDiv.appendChild(p2);

      resultsDiv.innerHTML = '';
      resultsDiv.appendChild(notFoundDiv);

      // Disable migration button
      document.getElementById("migrationSubmit").disabled = true;
    }
  } catch (error) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error';
    errorDiv.textContent = 'Error checking account: ' + error.message;
    resultsDiv.innerHTML = '';
    resultsDiv.appendChild(errorDiv);
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
          // Create success div
          const successDiv = document.createElement('div');
          successDiv.className = 'success';

          const header = document.createElement('h4');
          header.textContent = '✅ Migration Successful';
          successDiv.appendChild(header);

          const messageP = document.createElement('p');
          messageP.textContent = result.message;
          successDiv.appendChild(messageP);

          const oldIdP = document.createElement('p');
          const oldIdStrong = document.createElement('strong');
          oldIdStrong.textContent = 'Old Discord ID:';
          oldIdP.appendChild(oldIdStrong);
          oldIdP.appendChild(document.createTextNode(' ' + result.old_discord_id));
          successDiv.appendChild(oldIdP);

          const newIdP = document.createElement('p');
          const newIdStrong = document.createElement('strong');
          newIdStrong.textContent = 'New Discord ID:';
          newIdP.appendChild(newIdStrong);
          newIdP.appendChild(document.createTextNode(' ' + result.new_discord_id));
          successDiv.appendChild(newIdP);

          const usernameP = document.createElement('p');
          const usernameStrong = document.createElement('strong');
          usernameStrong.textContent = 'New Username:';
          usernameP.appendChild(usernameStrong);
          usernameP.appendChild(document.createTextNode(' ' + result.new_discord_username));
          successDiv.appendChild(usernameP);

          const resultsContainer = document.getElementById("migrationResults");
          resultsContainer.innerHTML = '';
          resultsContainer.appendChild(successDiv);

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
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error';
        errorDiv.textContent = 'Migration failed: ' + error.message;
        const resultsContainer = document.getElementById("migrationResults");
        resultsContainer.innerHTML = '';
        resultsContainer.appendChild(errorDiv);
      }
    });
  }
});
