/**
 * Prev/next arrows for the bike detail image gallery.
 * Progressive enhancement: if this file fails to load the arrows are inert
 * but the strip remains swipeable/scrollable.
 */
(function () {
  const gallery = document.querySelector('.gallery');
  const prevBtn = document.querySelector('.gallery-nav__arrow--prev');
  const nextBtn = document.querySelector('.gallery-nav__arrow--next');
  if (!gallery || !prevBtn || !nextBtn) return;

  const images = Array.from(gallery.querySelectorAll('.gallery__image'));
  const EPS = 2; // px slop: snap can leave sub-pixel scroll offsets

  // offsetLeft is relative to .gallery (its offsetParent, via position: relative),
  // so it's directly comparable to gallery.scrollLeft regardless of each
  // image's varying width.
  function scrollToImage(img) {
    gallery.scrollTo({ left: img.offsetLeft, behavior: 'smooth' });
  }

  // Next slide = first image whose left edge is beyond the viewport's left edge.
  function getNextImage() {
    return images.find(function (img) {
      return img.offsetLeft > gallery.scrollLeft + EPS;
    }) || null;
  }

  // Prev slide = last image whose left edge is still left of the viewport's left edge.
  // offsetLeft is strictly increasing in DOM order, so a linear scan can break early.
  function getPrevImage() {
    var prev = null;
    for (var i = 0; i < images.length; i++) {
      if (images[i].offsetLeft < gallery.scrollLeft - EPS) {
        prev = images[i];
      } else {
        break;
      }
    }
    return prev;
  }

  function updateArrows() {
    var scrollable = gallery.scrollWidth > gallery.clientWidth + 1;
    prevBtn.disabled = !scrollable || !getPrevImage();
    nextBtn.disabled = !scrollable || !getNextImage();
  }

  prevBtn.addEventListener('click', function () {
    var img = getPrevImage();
    if (img) scrollToImage(img);
  });

  nextBtn.addEventListener('click', function () {
    var img = getNextImage();
    if (img) scrollToImage(img);
  });

  // Debounced rather than raw: updates once per settled scroll (clicks,
  // trackpad swipes, and the smooth scroll's tail).
  var scrollTimer = null;
  gallery.addEventListener('scroll', function () {
    clearTimeout(scrollTimer);
    scrollTimer = setTimeout(updateArrows, 100);
  });

  // Widths settle after thumbnails finish loading and after column resizes.
  window.addEventListener('resize', updateArrows);
  window.addEventListener('load', updateArrows);

  updateArrows();
})();
