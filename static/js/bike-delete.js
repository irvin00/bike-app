/**
 * Delete bikes from the home grid (X on each card) and the detail page
 * ("Delete Bike" button). Both surfaces share the confirm + DELETE call;
 * the grid removes the card locally, the detail page redirects home.
 */
(function () {
  const grid = document.getElementById('bike-grid');
  const detailBtn = document.getElementById('delete-bike-btn');
  if (!grid && !detailBtn) return;

  async function deleteBike(id, name, onSuccess) {
    if (!confirm('Delete "' + name + '"? This also removes its photos and maintenance history.')) return;
    try {
      await api.del('/api/bikes/' + id); // api.del surfaces the server 404 detail
      onSuccess();
    } catch (err) {
      alert('Failed to delete bike: ' + err.message);
    }
  }

  if (grid) {
    const emptyState = document.getElementById('empty-state');
    const updateEmptyState = function () {
      emptyState.style.display =
        grid.querySelectorAll('.bike-card').length ? 'none' : '';
    }; // copy is already server-rendered status-aware; just toggle display

    grid.addEventListener('click', function (e) {
      const delBtn = e.target.closest('.bike-card__delete');
      if (!delBtn) return;
      const card = delBtn.closest('.bike-card');
      deleteBike(delBtn.dataset.bikeId, delBtn.dataset.bikeName, function () {
        card.remove();
        updateEmptyState();
      });
    });
  }

  if (detailBtn) {
    detailBtn.addEventListener('click', function () {
      deleteBike(detailBtn.dataset.bikeId, detailBtn.dataset.bikeName, function () {
        window.location.href = '/'; // the bike no longer exists
      });
    });
  }
})();
