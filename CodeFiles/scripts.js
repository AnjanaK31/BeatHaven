const API_URL = 'http://localhost:5000/api/songs';
const genres = ['Pop', 'Rock', 'Hip-Hop', 'Jazz', 'Classical', 'EDM', 'Indie'];

// State management
let allSongs = [];
let filteredSongs = [];
let currentView = 'all'; // 'all' or 'top'
let currentSongId = null; // Keep track of the song ID in the modal
let userRatings = JSON.parse(localStorage.getItem('userRatings') || '{}');
let currentPage = 1;
let itemsPerPage = 12;
let artists = [];
let albumArtCache = {}; // Cache for album art URLs

// Current year for generating reasonable random years
const currentYear = new Date().getFullYear();

async function loadAllSongs() {
  const songsContainer = document.getElementById('songsContainer');
  const resultsCount = document.getElementById('resultsCount');
  songsContainer.innerHTML = '<div class="loading">Connecting to library...</div>';
  resultsCount.textContent = 'Loading songs...';

  try {
    // Add timeout for fetch to prevent hanging
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout

    let res;
    try {
      res = await fetch(API_URL, { signal: controller.signal });
      clearTimeout(timeoutId);
    } catch (error) {
      // Handle fetch errors (network issue, timeout, CORS)
      console.warn('API request failed:', error.name, error.message);
      resultsCount.textContent = 'Error connecting to API. Using sample data.';
      songsContainer.innerHTML = '<div class="loading">Could not connect to the music server. Displaying sample songs.</div>';
      return useSampleData(); // Fallback to sample data
    }

    if (!res.ok) {
      // Handle HTTP errors (like 404, 500)
      console.warn(`API returned HTTP error! Status: ${res.status}`);
      resultsCount.textContent = `API Error (${res.status}). Using sample data.`;
      songsContainer.innerHTML = `<div class="loading">Server error ${res.status}. Displaying sample songs.</div>`;
      return useSampleData(); // Fallback to sample data
    }

    let songs = await res.json();
    songsContainer.innerHTML = '<div class="loading">Processing songs...</div>';

    // Generate random data for songs if needed and sanitize
    songs = songs.map(song => {
      const validId = parseInt(song.id); // Use ID for consistent random generation if needed
      const genreIndex = isNaN(validId) ? Math.floor(Math.random() * genres.length) : validId % genres.length;

      // Use provided value or generate random fallback
      const durationInSeconds = song.duration || (Math.floor(Math.random() * 180) + 120); // 2-5 mins
      const releaseYear = song.year || Math.floor(Math.random() * (currentYear - 1960 + 1)) + 1960;
      const ratingValue = song.rating || (Math.random() * 4 + 1).toFixed(1); // Ensure rating is 1-5
      const genreValue = song.genre || genres[genreIndex];
      const titleValue = song.title || song.name || 'Unknown Title';
      const artistValue = song.artist || song.artists || "Unknown Artist"; // Keep raw for now

      return {
        ...song, // Keep original fields
        id: song.id, // Ensure ID is present
        title: titleValue,
        artist: artistValue, // Store raw artist data
        rating: parseFloat(ratingValue).toFixed(1), // Ensure rating is number string
        genre: genreValue,
        duration: durationInSeconds,
        year: releaseYear
      };
    });

    allSongs = songs;
    populateFilterOptions(); // Populate filters before first filterSongs call
    filterSongs(); // Apply default filters (none) and display
    // Removed call to undefined setupYearFilter()

  } catch (error) {
    // Catch any other unexpected errors during processing
    console.error('Error loading or processing songs:', error);
    resultsCount.textContent = 'Error loading songs. Using sample data.';
    songsContainer.innerHTML = '<div class="loading">An error occurred. Displaying sample songs.</div>';
    useSampleData(); // Fallback to sample data
  }
}

// Helper function to safely parse artist data
function parseArtist(artistRaw) {
    if (Array.isArray(artistRaw)) {
        return artistRaw; // Already an array
    }
    if (typeof artistRaw === 'string') {
        if (artistRaw.startsWith("['") && artistRaw.endsWith("']")) {
            try {
                // Attempt to parse Python-style list string
                return JSON.parse(artistRaw.replace(/'/g, '"'));
            } catch (e) {
                 // Parsing failed, return the original string
                return [artistRaw];
            }
        }
        // Assume comma-separated string or single artist
        return artistRaw.split(',').map(a => a.trim()).filter(Boolean);
    }
    // Fallback for other types or undefined
    return ["Unknown Artist"];
}

function populateFilterOptions() {
  // Populate genre filter
  const genreFilter = document.getElementById('genreFilter');
  genreFilter.innerHTML = '<option value="">All Genres</option>'; // Reset options

  const uniqueGenres = [...new Set(allSongs.map(song => song.genre))].filter(Boolean).sort();
  uniqueGenres.forEach(genre => {
    const option = document.createElement('option');
    option.value = genre;
    option.textContent = genre;
    genreFilter.appendChild(option);
  });

  // Populate artist filter
  const artistFilter = document.getElementById('artistFilter');
  artistFilter.innerHTML = '<option value="">All Artists</option>'; // Reset options

  const artistSet = new Set();
  allSongs.forEach(song => {
    const parsedArtists = parseArtist(song.artist); // Use helper
    parsedArtists.forEach(a => artistSet.add(a));
  });

  artists = [...artistSet].filter(Boolean).sort();
  artists.forEach(artist => {
    const option = document.createElement('option');
    option.value = artist;
    option.textContent = artist;
    artistFilter.appendChild(option);
  });
}


function updateSongFilters() {
  let searchPool = allSongs;

  const searchTerm = document.getElementById('searchBar').value.toLowerCase();
  const selectedGenre = document.getElementById('genreFilter').value;
  const selectedArtist = document.getElementById('artistFilter').value;
  const minDuration = document.getElementById('minDuration').value;
  const maxDuration = document.getElementById('maxDuration').value;
  const minRating = document.getElementById('ratingFilter').value;
  const minYear = document.getElementById('minYear').value;
  const maxYear = document.getElementById('maxYear').value;

  filteredSongs = searchPool.filter(song => {
    const title = (song.title || '').toLowerCase();
    const parsedArtists = parseArtist(song.artist); // Use helper
    const artistString = parsedArtists.join(', ').toLowerCase();
    const genre = (song.genre || '').toLowerCase();

    // Search term filter (title, artist, genre)
    const matchesSearch = !searchTerm ||
                          title.includes(searchTerm) ||
                          artistString.includes(searchTerm) ||
                          genre.includes(searchTerm);

    // Genre filter
    const matchesGenre = !selectedGenre || song.genre === selectedGenre;

    // Artist filter
    const matchesArtist = !selectedArtist || parsedArtists.includes(selectedArtist);

    // Duration filter
    const songDuration = song.duration || 0;
    const matchesMinDuration = !minDuration || songDuration >= parseInt(minDuration);
    const matchesMaxDuration = !maxDuration || songDuration <= parseInt(maxDuration);

    // Year filter
    const songYear = song.year || 0;
    const matchesMinYear = !minYear || songYear >= parseInt(minYear);
    const matchesMaxYear = !maxYear || songYear <= parseInt(maxYear);

    // Rating filter
    // Use parseFloat for comparison, ensure song.rating is treated as number
    const songRating = parseFloat(song.rating);
    const matchesRating = !minRating || (!isNaN(songRating) && songRating >= parseFloat(minRating));


    return matchesSearch && matchesGenre && matchesArtist &&
           matchesMinDuration && matchesMaxDuration &&
           matchesMinYear && matchesMaxYear && matchesRating;
  });

  // Sort based on current view
  sortFilteredSongs();

  currentPage = 1; // Reset to first page on new filter
  updatePagination();
  displayCurrentPageSongs();
}

// Separate sorting logic
function sortFilteredSongs() {
    if (currentView === 'top') {
        // Sort by rating descending (treat rating as number)
        filteredSongs.sort((a, b) => parseFloat(b.rating) - parseFloat(a.rating));
    } else {
        // Default sort for 'all' view (e.g., by title)
        filteredSongs.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
    }
}


function filterSongs() {
  updateSongFilters();
}

function displayCurrentPageSongs() {
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentPageSongs = filteredSongs.slice(startIndex, endIndex);

  displaySongs(currentPageSongs); // Async function, will complete rendering over time

  // Update results count immediately
  const resultsCount = document.getElementById('resultsCount');
  if (filteredSongs.length === 0) {
      resultsCount.textContent = 'No songs match your filters.';
  } else {
      resultsCount.textContent =
          `Showing ${startIndex + 1}-${Math.min(endIndex, filteredSongs.length)} of ${filteredSongs.length} songs`;
  }

  // Update page info immediately
  const totalPages = Math.ceil(filteredSongs.length / itemsPerPage) || 1; // Ensure at least 1 page
  document.getElementById('pageInfo').textContent =
    `Page ${currentPage} of ${totalPages}`;

  // Update pagination buttons state
  updatePagination();
}


function updatePagination() {
  const totalPages = Math.ceil(filteredSongs.length / itemsPerPage);
  document.getElementById('prevPage').disabled = currentPage <= 1;
  document.getElementById('nextPage').disabled = currentPage >= totalPages;
}

async function getAlbumArt(artist, album) {
  // Use cache if available
  const cacheKey = `${artist}|${album}`;
  if (albumArtCache[cacheKey]) {
    return albumArtCache[cacheKey];
  }
  // Return placeholder immediately if no artist/album
  if (!artist || artist === "Unknown Artist" || !album) return 'placeholder';

  const searchTerm = `${artist} ${album}`.replace(/ /g, '+');
  // Use HTTPS for iTunes API
  const url = `https://itunes.apple.com/search?term=${searchTerm}&entity=album&limit=1`;

  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    if (data.resultCount > 0 && data.results[0].artworkUrl100) {
      // Get higher resolution image by modifying URL
      let artworkUrl = data.results[0].artworkUrl100.replace('100x100bb', '300x300bb');
      albumArtCache[cacheKey] = artworkUrl; // Cache the result
      return artworkUrl;
    } else {
      albumArtCache[cacheKey] = 'placeholder'; // Cache placeholder if not found
      return 'placeholder'; // Indicate placeholder needed
    }
  } catch (error) {
    console.error('Error fetching album art for:', artist, album, error);
    albumArtCache[cacheKey] = 'placeholder'; // Cache placeholder on error
    return 'placeholder'; // Indicate placeholder needed
  }
}

async function displaySongs(songList) {
  const container = document.getElementById('songsContainer');
  container.innerHTML = ''; // Clear previous songs

  if (songList.length === 0 && allSongs.length > 0) { // Only show 'no results' if songs have loaded
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 40px;">
        <p>No songs found matching your criteria.</p>
      </div>
    `;
    return;
  }
  if (songList.length === 0 && allSongs.length === 0) {
      // Handles the initial loading state or if API/sample fails completely
      if (!container.querySelector('.loading')) { // Avoid overwriting specific loading messages
         container.innerHTML = '<div class="loading">Loading songs...</div>';
      }
      return;
  }

  // Create song card elements (without waiting for all album art)
  const songCardPromises = songList.map(async (song) => {
    const parsedArtists = parseArtist(song.artist); // Use helper
    const artistName = parsedArtists.join(', ');

    // Format duration
    const minutes = Math.floor(song.duration / 60);
    const seconds = String(song.duration % 60).padStart(2, '0');
    const formattedDuration = `${minutes}:${seconds}`;

    const songCard = document.createElement('div');
    songCard.className = 'song-card';
    songCard.setAttribute('data-song-id', song.id); // Add data attribute for later reference

    // Initial HTML with placeholder
    songCard.innerHTML = `
      <div class="song-info">
        <div class="song-cover placeholder">🎵</div>
        <div>
          <h3 class="song-title">${song.title}</h3>
          <p class="song-meta">by ${artistName}</p>
          <p class="song-meta">Genre: ${song.genre || 'N/A'}</p>
          <p class="song-meta">Year: ${song.year || 'N/A'}</p>
          <p class="song-meta">Duration: ${formattedDuration}</p>
          <p class="song-meta">Rating: <span class="rating">★</span> ${song.rating}/5</p>
          ${userRatings[song.id] ? `<p class="song-meta your-rating">Your Rating: <span class="rating">★</span> ${userRatings[song.id]}/5</p>` : ''}
        </div>
      </div>
    `;

    songCard.addEventListener('click', () => openSongDetails(song));
    container.appendChild(songCard); // Append card immediately

    // Fetch album art asynchronously and update the card
    const albumArtUrl = await getAlbumArt(artistName, song.album || song.title);
    const imgContainer = songCard.querySelector('.song-cover');
    if (albumArtUrl && albumArtUrl !== 'placeholder' && imgContainer) {
        imgContainer.innerHTML = `<img src="${albumArtUrl}" alt="Album Art" class="song-cover-img" />`;
        // Add styling for song-cover-img if needed in CSS (e.g., width, height, object-fit)
        imgContainer.classList.remove('placeholder');
        const imgElement = imgContainer.querySelector('img');
        imgElement.style.width = '100%'; // Ensure image fills container
        imgElement.style.height = '100%';
        imgElement.style.objectFit = 'cover';
        imgElement.style.borderRadius = '4px'; // Match placeholder style if needed
    } else if (imgContainer) {
        imgContainer.classList.add('placeholder'); // Ensure placeholder class if no art
        imgContainer.innerHTML = '🎵'; // Reset to icon if fetch failed after initial append
    }
  });

  // Wait for all cards to be created and appended (though art updates later)
  await Promise.all(songCardPromises);
}


async function openSongDetails(song) {
  currentSongId = song.id; // Store ID for rating updates

  const parsedArtists = parseArtist(song.artist); // Use helper
  const artistName = parsedArtists.join(', ');

  // Format duration
  const minutes = Math.floor(song.duration / 60);
  const seconds = String(song.duration % 60).padStart(2, '0');
  const formattedDuration = `${minutes}:${seconds}`;

  // Fetch album art specifically for the modal (can reuse cache)
  const albumArtUrl = await getAlbumArt(artistName, song.album || song.title);
  const albumArtHtml = (albumArtUrl && albumArtUrl !== 'placeholder') ?
    `<img src="${albumArtUrl}" alt="Album Art" class="modal-album-art" />` :
    '<div class="modal-album-art placeholder">🎵</div>';

  // Get random description (as before)
  const descriptions = [
    "A captivating melody that takes listeners on an emotional journey through sound and rhythm.",
    "An upbeat track with infectious hooks and memorable lyrics that stick with you.",
    "A masterful blend of traditional and modern elements, creating a unique sonic experience.",
    "A soulful performance that showcases the artist's incredible vocal range and emotional depth.",
    "An innovative composition that pushes the boundaries of the genre in exciting ways."
  ];
  const randomDescription = descriptions[Math.floor(Math.random() * descriptions.length)];

  // Create modal HTML
  const modal = document.createElement('div');
  modal.className = 'modal';
  modal.id = 'songDetailModal';
  modal.innerHTML = `
    <div class="modal-content">
      <span class="close-button">×</span>
      <div class="song-details">
        ${albumArtHtml}
        <div class="song-details-info">
          <h2>${song.title}</h2>
          <p><strong>Artist:</strong> ${artistName}</p>
          <p><strong>Album:</strong> ${song.album || 'Unknown Album'}</p>
          <p><strong>Genre:</strong> ${song.genre || 'N/A'}</p>
          <p><strong>Year:</strong> ${song.year || 'N/A'}</p>
          <p><strong>Duration:</strong> ${formattedDuration}</p>
          <p><strong>Rating:</strong> <span class="rating">★</span> ${song.rating}/5</p>
          <p class="song-description">${randomDescription}</p>

          <div class="user-rating">
            <p>Your Rating:</p>
            <div class="star-rating">
              ${[1, 2, 3, 4, 5].map(star => `
                <span class="star ${userRatings[song.id] >= star ? 'active' : ''}" data-value="${star}">★</span>
              `).join('')}
            </div>
            <button id="clearRatingBtn" style="${!userRatings[song.id] ? 'display: none;' : ''}">Clear Rating</button>
          </div>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(modal);
  // Add slight delay before adding class to allow CSS transition
  requestAnimationFrame(() => {
    modal.style.display = 'block'; // Show the modal
  });


  // --- Modal Event Listeners ---

  const closeModal = () => {
    const modalElement = document.getElementById('songDetailModal');
    if (modalElement) {
        modalElement.style.display = 'none'; // Hide the modal
        document.body.removeChild(modalElement);
    }
     // Remove the window click listener specific to this modal instance
    window.removeEventListener('click', outsideClickHandler);
  };

  // Close button
  const closeButton = modal.querySelector('.close-button');
  closeButton.addEventListener('click', closeModal);

  // Click outside modal content
  const outsideClickHandler = (event) => {
    if (event.target === modal) {
      closeModal();
    }
  };
  window.addEventListener('click', outsideClickHandler);


  // Star rating click listener
  const stars = modal.querySelectorAll('.star-rating .star');
  stars.forEach(star => {
    star.addEventListener('click', () => {
      const selectedRating = parseInt(star.getAttribute('data-value'));
      const currentSongIdStr = String(currentSongId); // Ensure consistency

      // Update rating or clear if clicking the same star again
      if (userRatings[currentSongIdStr] === selectedRating) {
        // Clear rating if clicking the same star again
        delete userRatings[currentSongIdStr];
        localStorage.setItem('userRatings', JSON.stringify(userRatings));
        updateStarDisplay(stars, 0); // Update stars in modal
        updateSongCardRating(currentSongIdStr, null); // Update grid card (null indicates cleared)
        document.getElementById('clearRatingBtn').style.display = 'none'; // Hide clear button
        return;
      }

      // Store rating locally
      userRatings[currentSongIdStr] = selectedRating;
      localStorage.setItem('userRatings', JSON.stringify(userRatings));

      // Update stars' visual state in modal
      updateStarDisplay(stars, selectedRating);
      document.getElementById('clearRatingBtn').style.display = 'inline-block'; // Show clear button

      // Update the rating on the corresponding song card in the grid
      updateSongCardRating(currentSongIdStr, selectedRating);
    });
  });

   // Clear Rating button listener
   const clearRatingBtn = modal.querySelector('#clearRatingBtn');
   clearRatingBtn.addEventListener('click', () => {
    const currentSongIdStr = String(currentSongId);
    if (userRatings[currentSongIdStr]) {
      // Clear rating from local storage
      delete userRatings[currentSongIdStr];
      localStorage.setItem('userRatings', JSON.stringify(userRatings));
      updateStarDisplay(stars, 0); // Reset stars in modal
      updateSongCardRating(currentSongIdStr, null); // Update grid card (null means clear)
      clearRatingBtn.style.display = 'none'; // Hide clear button
    }
   });
}

// Helper function to update star display in the modal
function updateStarDisplay(starElements, rating) {
     starElements.forEach(s => {
        const starValue = parseInt(s.getAttribute('data-value'));
        s.classList.toggle('active', rating >= starValue);
      });
}


// Function to update the "Your Rating" display on a specific song card
function updateSongCardRating(songId, rating) {
  // Find the card using the data-song-id attribute
  const songCard = document.querySelector(`.song-card[data-song-id="${songId}"]`);
  if (!songCard) return; // Card might not be on the current page

  let ratingDisplay = songCard.querySelector('.your-rating');

  if (rating !== null) {
    // Update or Add the rating display
    const ratingHtml = `Your Rating: <span class="rating">★</span> ${rating}/5`;
    if (ratingDisplay) {
      ratingDisplay.innerHTML = ratingHtml;
    } else {
      // Create the element if it doesn't exist
      const lastMeta = songCard.querySelector('.song-meta:last-of-type'); // Find last meta element
      if(lastMeta) {
          ratingDisplay = document.createElement('p');
          ratingDisplay.className = 'song-meta your-rating';
          ratingDisplay.innerHTML = ratingHtml;
          // Insert after the last standard meta tag
          lastMeta.parentNode.insertBefore(ratingDisplay, lastMeta.nextSibling);
      }
    }
  } else {
      // Remove the rating display if rating is cleared (null)
      if(ratingDisplay) {
          ratingDisplay.remove();
      }
  }

  // Optional: Re-apply filters if a rating filter is active
  const minRatingFilter = document.getElementById('ratingFilter').value;
   // And if the current view is top rated, re-sort
  if (minRatingFilter !== '' || currentView === 'top') {
    // Re-filter and re-display might be too disruptive.
    // A less disruptive approach might be to just re-sort the *current* view if needed.
    if (currentView === 'top') {
        sortFilteredSongs(); // Re-sort the filtered list
        displayCurrentPageSongs(); // Re-display the current page with new order
    }
    // If filtering by rating, the change might make the song appear/disappear
    // filterSongs(); // Uncomment this for full re-filter if required by rating filters
  }
}


// Debounce utility
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func.apply(this, args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Initialize filter event listeners
function initializeFilters() {
  document.getElementById('searchBar').addEventListener('input', debounce(filterSongs, 300));
  document.getElementById('genreFilter').addEventListener('change', filterSongs);
  document.getElementById('artistFilter').addEventListener('change', filterSongs);
  document.getElementById('minDuration').addEventListener('input', debounce(filterSongs, 500));
  document.getElementById('maxDuration').addEventListener('input', debounce(filterSongs, 500));
  document.getElementById('minYear').addEventListener('input', debounce(filterSongs, 500));
  document.getElementById('maxYear').addEventListener('input', debounce(filterSongs, 500));
  document.getElementById('ratingFilter').addEventListener('change', filterSongs); // Change is better for select

  // Reset filters button
  document.getElementById('resetFilters').addEventListener('click', clearAllFilters);

  // View toggle buttons
  document.getElementById('allSongsView').addEventListener('click', () => changeView('all'));
  document.getElementById('topRatedView').addEventListener('click', () => changeView('top'));

  // Pagination controls
  document.getElementById('prevPage').addEventListener('click', () => changePage(-1));
  document.getElementById('nextPage').addEventListener('click', () => changePage(1));
}

// Function to clear all filters
function clearAllFilters() {
  document.getElementById('searchBar').value = '';
  document.getElementById('genreFilter').value = '';
  document.getElementById('artistFilter').value = '';
  document.getElementById('minDuration').value = '';
  document.getElementById('maxDuration').value = '';
  document.getElementById('ratingFilter').value = '';
  document.getElementById('minYear').value = '';
  document.getElementById('maxYear').value = '';

  // No slider to reset in this version

  filterSongs(); // Re-apply filters (which should now be empty)
}

// Function to change page
function changePage(direction) {
  const totalPages = Math.ceil(filteredSongs.length / itemsPerPage);
  const newPage = currentPage + direction;

  // Ensure newPage is within valid bounds
  if (newPage >= 1 && newPage <= totalPages) {
    currentPage = newPage;
    // updatePagination(); // Called within displayCurrentPageSongs
    displayCurrentPageSongs();
    window.scrollTo(0, 0); // Scroll to top on page change
  }
}

// Function to change view between all songs and top rated
function changeView(view) {
  if (currentView === view) return; // No change if already on this view

  currentView = view;
  document.getElementById('allSongsView').classList.toggle('active', view === 'all');
  document.getElementById('topRatedView').classList.toggle('active', view === 'top');

  // Update the title based on the view
  document.getElementById('viewTitle').textContent = view === 'top' ? 'Top Rated Songs' : 'Music Library';

  // Re-sort the currently filtered songs based on the new view
  sortFilteredSongs();

  currentPage = 1; // Reset to first page when changing views
  // updatePagination(); // Called within displayCurrentPageSongs
  displayCurrentPageSongs();
}


// Sample data function (remains largely the same)
function useSampleData() {
  console.log('Using sample data');
  const sampleSongs = [];
  const sampleArtists = ['The Beatles', 'Queen', 'Michael Jackson', 'Taylor Swift', 'Beyoncé', 'Ed Sheeran', 'Adele', 'Drake', 'BTS', 'Dua Lipa', 'Bob Dylan', 'Miles Davis'];
  const sampleAlbums = ['Greatest Hits', 'Revolution', 'Harmony', 'Midnight Tales', 'Eternal', 'Dreamland', 'Echoes', 'New Beginnings', 'Golden Age', 'Starlight'];

  for (let i = 1; i <= 50; i++) { // Increased sample size
    const artistIndex = Math.floor(Math.random() * sampleArtists.length);
    const albumIndex = Math.floor(Math.random() * sampleAlbums.length);
    const genreIndex = Math.floor(Math.random() * genres.length);
    const year = Math.floor(Math.random() * (currentYear - 1960 + 1)) + 1960;
    const duration = Math.floor(Math.random() * 180) + 120; // 120-300 seconds
    const rating = (Math.random() * 4 + 1).toFixed(1); // 1.0 - 5.0

    sampleSongs.push({
      id: `sample-${i}`, // Use unique string IDs for samples
      title: `Sample Song ${i}`,
      artist: sampleArtists[artistIndex],
      album: sampleAlbums[albumIndex],
      genre: genres[genreIndex],
      year: year,
      duration: duration,
      rating: rating
    });
  }

  allSongs = sampleSongs;
  populateFilterOptions(); // Populate filters first
  filterSongs(); // Apply default filters and display
  // Removed call to undefined setupYearFilter()

  return sampleSongs; // Return for potential chaining if needed elsewhere
}

// --- Initial Load ---
document.addEventListener('DOMContentLoaded', () => {
  initializeFilters();
  loadAllSongs(); // Start loading data when the DOM is ready
});

// Function to update username display
function updateUsernameDisplay() {
  const usernameSpan = document.querySelector('.username');
  const userNav = document.querySelector('.user-nav');
  const token = localStorage.getItem('token');
  
  if (token) {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      usernameSpan.textContent = payload.username;
      userNav.style.display = 'flex';
    } catch (error) {
      console.error('Error decoding token:', error);
      userNav.style.display = 'none';
    }
  } else {
    userNav.style.display = 'none';
  }
}

// Function to handle logout
function handleLogout() {
  localStorage.removeItem('token');
  updateUsernameDisplay();
  window.location.href = '/login.html';
}

// Function to handle dashboard navigation
function handleDashboard() {
  window.location.href = '/dashboard.html';
}

// Add event listener for logout button
document.addEventListener('DOMContentLoaded', () => {
  const logoutBtn = document.querySelector('.logout-btn');
  const dashboardBtn = document.querySelector('.dashboard-btn');
  
  if (logoutBtn) {
    logoutBtn.addEventListener('click', handleLogout);
  }
  
  if (dashboardBtn) {
    dashboardBtn.addEventListener('click', handleDashboard);
  }
  
  updateUsernameDisplay();
});