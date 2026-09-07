// Mobile nav toggle
document.addEventListener('DOMContentLoaded', () => {
  const header = document.querySelector('.site-header');
  const toggle = document.querySelector('.menu-toggle');
  if (toggle && header) {
    toggle.addEventListener('click', () => {
      const isOpen = header.classList.toggle('nav-open');
      toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });
  }

  // Close mobile nav on link click
  document.querySelectorAll('.nav-links a').forEach(link => {
    link.addEventListener('click', () => header && header.classList.remove('nav-open'));
  });

  // Passport photo upload (used on membership.html register form)
  const photoBox = document.getElementById('reg-photo-box');
  const photoInput = document.getElementById('reg-photo');
  const photoPreview = document.getElementById('reg-photo-preview');
  const photoLabel = document.getElementById('reg-photo-label');

  if (photoBox && photoInput) {
    photoBox.addEventListener('click', () => photoInput.click());

    photoInput.addEventListener('change', () => {
      const file = photoInput.files[0];
      if (!file) return;

      if (file.size > 2 * 1024 * 1024) {
        alert('Please choose an image under 2MB.');
        photoInput.value = '';
        return;
      }

      const reader = new FileReader();
      reader.onload = (e) => {
        photoPreview.src = e.target.result;
        photoPreview.style.display = 'block';
        photoLabel.textContent = file.name;
      };
      reader.readAsDataURL(file);
    });
  }
  document.querySelectorAll('.faq-item').forEach(item => {
    const q = item.querySelector('.faq-q');
    q && q.addEventListener('click', () => {
      const isOpen = item.classList.contains('open');
      document.querySelectorAll('.faq-item.open').forEach(i => i !== item && i.classList.remove('open'));
      item.classList.toggle('open', !isOpen);
    });
  });
});

// Membership tabs (used on membership.html)
document.addEventListener('DOMContentLoaded', () => {
  const tabs = document.querySelectorAll('.member-tab-btn');
  const panels = document.querySelectorAll('.member-panel');
  function activate(target) {
    tabs.forEach(t => t.classList.toggle('active', t.dataset.target === target));
    panels.forEach(p => p.classList.toggle('active', p.id === target));
  }
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      activate(tab.dataset.target);
      history.replaceState(null, '', '#' + tab.dataset.target);
    });
  });
  const hash = window.location.hash.replace('#', '');
  if (hash === 'login' || hash === 'register') activate(hash);

  // Demo-only form submit handling (no backend yet)
  document.querySelectorAll('form[data-demo-form]').forEach(form => {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      alert('This form is a working template. It will be connected to a backend once that part of the project is scoped.');
    });
  });
});
