const toggle = document.querySelector('.menu-toggle');
const links = document.querySelector('.nav-links');
if (toggle && links) {
  toggle.addEventListener('click', () => {
    const expanded = toggle.getAttribute('aria-expanded') === 'true';
    toggle.setAttribute('aria-expanded', String(!expanded));
    links.classList.toggle('open', !expanded);
  });
}
for (const form of document.querySelectorAll('form[data-confirm]')) {
  form.addEventListener('submit', (event) => {
    if (!confirm(form.dataset.confirm)) event.preventDefault();
  });
}
const total = document.querySelector('#order-total');
const size = document.querySelector('#size');
const quantity = document.querySelector('#quantity');
if (total && size && quantity) {
  const update = () => {
    const unit = Number(total.dataset.price) + (size.value === 'Large' ? 100 : 0);
    const count = Math.max(1, Math.min(10, Number(quantity.value) || 1));
    total.textContent = '$' + ((unit * count) / 100).toFixed(2);
  };
  size.addEventListener('change', update);
  quantity.addEventListener('input', update);
}
