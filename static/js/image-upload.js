/**
 * Image management on the edit-bike form: drag-and-drop upload zone,
 * primary selection, reorder, delete. Local DOM mutation from API
 * responses (no list refetch on success); a GET re-render is the error
 * recovery path — never location.reload(), which would wipe unsaved
 * form fields.
 */
(function () {
  const zone = document.getElementById('upload-zone');
  const list = document.getElementById('image-list');
  if (!zone || !list) return; // create mode — nothing to manage yet

  const bikeId = list.dataset.bikeId;
  const fileInput = document.getElementById('image-file-input');

  // --- Helpers ---

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // Mirror of the Jinja row in bike_form.html.j2, built from API data.
  function createRowEl(image) {
    const div = document.createElement('div');
    div.className = 'image-row' + (image.is_primary ? ' is-primary' : '');
    div.dataset.imageId = image.id;
    div.innerHTML =
      '<span class="image-row__handle" draggable="true" title="Drag to reorder">&vArr;</span>' +
      '<img src="' + escapeHtml(image.thumb_url) + '" alt="' + escapeHtml(image.original_name) + '">' +
      '<button type="button" class="image-row__primary" data-image-id="' + image.id + '" title="Make primary">' +
        (image.is_primary ? '★' : '☆') + '</button>' +
      '<button type="button" class="image-row__delete" data-image-id="' + image.id + '" title="Delete image">&times;</button>';
    return div;
  }

  function starRow(row) {
    const prev = list.querySelector('.image-row.is-primary');
    if (prev) {
      prev.classList.remove('is-primary');
      prev.querySelector('.image-row__primary').textContent = '☆';
    }
    row.classList.add('is-primary');
    row.querySelector('.image-row__primary').textContent = '★';
  }

  function renderFromApi(bike) {
    list.innerHTML = '';
    bike.images.forEach(function (img) {
      list.appendChild(createRowEl(img));
    });
  }

  // --- Upload ---

  async function uploadFiles(fileList) {
    if (!fileList.length) return;
    const fd = new FormData();
    for (const f of fileList) fd.append('files', f);
    try {
      const created = await api.upload('/api/bikes/' + bikeId + '/images', fd);
      // Batch is all-or-nothing server-side, so append the whole result.
      created.forEach(function (img) {
        list.appendChild(createRowEl(img));
      });
    } catch (err) {
      alert('Upload failed: ' + err.message);
    }
  }

  zone.addEventListener('click', function () {
    fileInput.click();
  });

  zone.addEventListener('dragover', function (e) {
    if (!e.dataTransfer.types.includes('Files')) return; // don't hijack text drags
    e.preventDefault();
    zone.classList.add('dragover');
  });

  zone.addEventListener('dragleave', function (e) {
    if (!zone.contains(e.relatedTarget)) zone.classList.remove('dragover');
  });

  zone.addEventListener('drop', function (e) {
    e.preventDefault();
    zone.classList.remove('dragover');
    if (e.dataTransfer.files.length) uploadFiles(e.dataTransfer.files);
  });

  fileInput.addEventListener('change', function () {
    uploadFiles(fileInput.files);
    fileInput.value = ''; // allow re-selecting the same file
  });

  // --- Primary + Delete (delegated) ---

  list.addEventListener('click', async function (e) {
    const starBtn = e.target.closest('.image-row__primary');
    if (starBtn) {
      const row = starBtn.closest('.image-row');
      if (row.classList.contains('is-primary')) return;
      try {
        const image = await api.patch(
          '/api/bikes/' + bikeId + '/images/' + starBtn.dataset.imageId,
          { is_primary: true }
        );
        starRow(row); // server response confirms; unstar the old primary locally
      } catch (err) {
        alert('Failed to set primary: ' + err.message);
      }
      return;
    }

    const delBtn = e.target.closest('.image-row__delete');
    if (!delBtn) return;

    if (!confirm('Delete this image?')) return;

    const row = delBtn.closest('.image-row');
    const wasPrimary = row.classList.contains('is-primary');
    try {
      await api.del('/api/bikes/' + bikeId + '/images/' + delBtn.dataset.imageId);
      row.remove();
      // Mirror the server's promotion rule (DELETE returns 204 with no
      // body): the first remaining row in DOM order is the new primary.
      if (wasPrimary) {
        const first = list.querySelector('.image-row');
        if (first) starRow(first);
      }
    } catch (err) {
      alert('Failed to delete: ' + err.message);
    }
  });

  // --- Reorder (HTML5 drag-and-drop on the handle) ---

  let dragId = null;
  let orderBefore = [];

  list.addEventListener('dragstart', function (e) {
    const handle = e.target.closest('.image-row__handle');
    if (!handle) return;
    const row = handle.closest('.image-row');
    dragId = Number(row.dataset.imageId);
    orderBefore = Array.from(list.querySelectorAll('.image-row'))
      .map(function (r) { return Number(r.dataset.imageId); });
    row.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', String(dragId)); // required for Firefox
  });

  list.addEventListener('dragover', function (e) {
    const row = e.target.closest('.image-row');
    if (!row || dragId == null || Number(row.dataset.imageId) === dragId) return;
    e.preventDefault(); // required to allow the drop
    const dragging = list.querySelector('.image-row.dragging');
    if (!dragging) return;
    const rect = row.getBoundingClientRect();
    const before = e.clientY < rect.top + rect.height / 2;
    if (before) {
      if (row.previousElementSibling !== dragging) list.insertBefore(dragging, row);
    } else {
      if (row.nextElementSibling !== dragging) list.insertBefore(dragging, row.nextElementSibling);
    }
  });

  list.addEventListener('drop', async function (e) {
    e.preventDefault();
    if (dragId == null) return;
    const orderAfter = Array.from(list.querySelectorAll('.image-row'))
      .map(function (r) { return Number(r.dataset.imageId); });
    // DOM order IS sort order; PATCH only the images whose index changed.
    const patches = [];
    orderAfter.forEach(function (id, idx) {
      if (orderBefore[idx] !== id) {
        patches.push(api.patch('/api/bikes/' + bikeId + '/images/' + id, { sort_order: idx }));
      }
    });
    try {
      await Promise.all(patches);
    } catch (err) {
      alert('Failed to save order: ' + err.message);
      try {
        const bike = await api.get('/api/bikes/' + bikeId);
        renderFromApi(bike);
      } catch (err2) {
        console.error('Resync failed', err2);
      }
    }
  });

  list.addEventListener('dragend', function () {
    const dragging = list.querySelector('.image-row.dragging');
    if (dragging) dragging.classList.remove('dragging');
    dragId = null;
  });
})();
