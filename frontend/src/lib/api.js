export async function authedFetch(getToken, input, init = {}) {
  const token = typeof getToken === 'function' ? await getToken() : null
  const headers = new Headers(init.headers || {})

  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  return fetch(input, {
    ...init,
    headers,
  })
}
