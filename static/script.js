document.addEventListener('DOMContentLoaded', () => {
  // Mobile Nav Toggle
  const mobileToggle = document.getElementById('mobileToggle');
  const navLinks = document.getElementById('navLinks');
  if (mobileToggle && navLinks) {
    mobileToggle.addEventListener('click', () => {
      navLinks.classList.toggle('open');
      const icon = mobileToggle.querySelector('i');
      if (icon) {
        icon.classList.toggle('fa-bars');
        icon.classList.toggle('fa-xmark');
      }
    });
  }

  // Dismiss Flash Alerts
  document.querySelectorAll('.alert .close-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const alert = e.target.closest('.alert');
      if (alert) {
        alert.style.opacity = '0';
        alert.style.transform = 'translateY(-10px)';
        setTimeout(() => alert.remove(), 200);
      }
    });
  });

  // Clipboard Copy Functionality
  window.copyToClipboard = function(text, btnElement, successMsg = 'COPIED!') {
    if (!navigator.clipboard) {
      // Fallback
      const textArea = document.createElement("textarea");
      textArea.value = text;
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand('copy');
        showCopyFeedback(btnElement, successMsg);
      } catch (err) {
        console.error('Fallback copy failed', err);
      }
      document.body.removeChild(textArea);
      return;
    }

    navigator.clipboard.writeText(text).then(() => {
      showCopyFeedback(btnElement, successMsg);
    }).catch(err => {
      console.error('Clipboard copy error:', err);
    });
  };

  function showCopyFeedback(btn, message) {
    if (!btn) return;
    const originalHtml = btn.innerHTML;
    btn.innerHTML = `<i class="fa-solid fa-check"></i> ${message}`;
    btn.classList.add('btn-primary');
    btn.classList.remove('btn-outline', 'btn-secondary');

    setTimeout(() => {
      btn.innerHTML = originalHtml;
      btn.classList.remove('btn-primary');
      btn.classList.add('btn-outline');
    }, 2000);
  }

  // Live Score Calculation Preview in Result Submit & Admin Edit
  const placementInput = document.getElementById('placementInput');
  const killsInput = document.getElementById('killsInput');
  const pointsPreview = document.getElementById('pointsPreview');

  if (placementInput && killsInput && pointsPreview) {
    const placementTable = [15, 12, 10, 8, 6, 5, 4, 3, 2, 1];

    function updatePreview() {
      const placement = parseInt(placementInput.value) || 0;
      const kills = parseInt(killsInput.value) || 0;
      const placePoints = (placement >= 1 && placement <= 10) ? placementTable[placement - 1] : 0;
      const killPoints = kills * 1;
      const total = placePoints + killPoints;

      pointsPreview.innerHTML = `
        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
          <span>Placement Points:</span> <strong>${placePoints} pts</strong>
        </div>
        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
          <span>Kill Points (${kills} kills):</span> <strong>${killPoints} pts</strong>
        </div>
        <div style="display:flex; justify-content:space-between; border-top:1px solid var(--border); padding-top:6px; color:var(--acid); font-size:1.1rem;">
          <span>Estimated Total:</span> <strong>${total} pts</strong>
        </div>
      `;
    }

    placementInput.addEventListener('input', updatePreview);
    killsInput.addEventListener('input', updatePreview);
    updatePreview();
  }

  // Join Match Modal Helper
  window.openJoinMatchModal = function(roomId, roomPass) {
    const modal = document.getElementById('joinMatchModal');
    if (!modal) return;
    const idEl = document.getElementById('modalRoomId');
    const passEl = document.getElementById('modalRoomPass');
    if (idEl && roomId) idEl.textContent = roomId;
    if (passEl && roomPass) passEl.textContent = roomPass;
    modal.showModal();
  };

  // Custom Room Release Countdown Timer
  const countdownEl = document.getElementById('roomCountdown');
  if (countdownEl && countdownEl.dataset.target) {
    const targetIso = countdownEl.dataset.target;
    const targetDate = new Date(targetIso).getTime();

    function updateCountdown() {
      const now = new Date().getTime();
      const diff = targetDate - now;

      if (isNaN(targetDate) || diff <= 0) {
        countdownEl.textContent = "00:00:00";
        countdownEl.style.color = "var(--acid)";
        // Auto-refresh page once release time is reached to display revealed credentials
        setTimeout(() => {
          window.location.reload();
        }, 1500);
        return;
      }

      const totalHours = Math.floor(diff / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);

      const pad = (num) => String(num).padStart(2, '0');
      countdownEl.textContent = `${pad(totalHours)}:${pad(minutes)}:${pad(seconds)}`;
    }

    updateCountdown();
    setInterval(updateCountdown, 1000);
  }
});
