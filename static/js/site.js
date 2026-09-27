const menuButton = document.querySelector('.menu-toggle');
const navigation = document.querySelector('#navigation');
if (menuButton && navigation) {
  menuButton.addEventListener('click', () => {
    const opened = navigation.classList.toggle('open');
    menuButton.setAttribute('aria-expanded', String(opened));
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      navigation.classList.remove('open');
      menuButton.setAttribute('aria-expanded', 'false');
    }
  });
}

const presentButton = document.querySelector('#all-present');
if (presentButton) {
  presentButton.addEventListener('click', () => {
    document.querySelectorAll('select[name$="-status"]').forEach(select => {
      if (!select.disabled && !select.value) select.value = 'present';
    });
  });
}
