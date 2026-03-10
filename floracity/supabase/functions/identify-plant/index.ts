import { serve } from 'https://deno.land/std@0.177.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const PLANT_ID_API_KEY = Deno.env.get('PLANT_ID_API_KEY')!;
const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!;
const SUPABASE_SERVICE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const authHeader = req.headers.get('Authorization');
    if (!authHeader) throw new Error('No authorization header');

    // Verify user via Supabase Auth
    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);
    const { data: { user }, error: authError } = await supabase.auth.getUser(
      authHeader.replace('Bearer ', '')
    );
    if (authError || !user) throw new Error('Unauthorized');

    const { photo_base64, location_lat, location_lng } = await req.json();
    if (!photo_base64) throw new Error('No photo provided');

    // Call Plant.id API v3
    const plantIdRes = await fetch('https://plant.id/api/v3/identification', {
      method: 'POST',
      headers: {
        'Api-Key': PLANT_ID_API_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        images: [photo_base64],
        similar_images: true,
        plant_details: ['common_names', 'url', 'wiki_description', 'taxonomy'],
        language: 'en',
        health: 'all',
      }),
    });

    if (!plantIdRes.ok) throw new Error(`Plant.id API error: ${plantIdRes.status}`);
    const plantIdData = await plantIdRes.json();

    const suggestions = plantIdData.result?.classification?.suggestions ?? [];
    if (suggestions.length === 0) {
      return new Response(
        JSON.stringify({ error: 'No plant recognized', suggestions: [] }),
        { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    // Return top 3 suggestions to the client for confidence-based UX
    const topSuggestions = suggestions.slice(0, 3).map((s: any) => ({
      scientific_name: s.name,
      common_name: s.details?.common_names?.[0] ?? null,
      family: s.details?.taxonomy?.family ?? null,
      description: s.details?.wiki_description?.value ?? null,
      wikipedia_url: s.details?.url ?? null,
      confidence: s.probability,
    }));

    // If top match is high confidence, auto-save the discovery
    const top = topSuggestions[0];
    if (top.confidence >= 0.6) {
      const result = await saveDiscovery({
        supabase,
        userId: user.id,
        plant: top,
        confidence: top.confidence,
        photo_base64,
        location_lat,
        location_lng,
      });
      return new Response(
        JSON.stringify({ ...result, suggestions: topSuggestions }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    return new Response(
      JSON.stringify({ needs_confirmation: true, suggestions: topSuggestions }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );
  } catch (err: any) {
    return new Response(
      JSON.stringify({ error: err.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );
  }
});

async function saveDiscovery({
  supabase, userId, plant, confidence, photo_base64, location_lat, location_lng
}: any) {
  // Check if plant species already exists in DB
  const { data: existingPlant } = await supabase
    .from('plants')
    .select('id, discovery_count, first_discovered_by')
    .eq('scientific_name', plant.scientific_name)
    .single();

  let plantId: string;
  let isPioneer = false;

  if (!existingPlant) {
    // First ever discovery of this species — Pioneer!
    isPioneer = true;
    const { data: newPlant, error } = await supabase
      .from('plants')
      .insert({
        scientific_name: plant.scientific_name,
        common_name: plant.common_name,
        family: plant.family,
        description: plant.description,
        wikipedia_url: plant.wikipedia_url,
        first_discovered_by: userId,
        first_discovered_at: new Date().toISOString(),
        discovery_count: 1,
      })
      .select('id')
      .single();
    if (error) throw error;
    plantId = newPlant.id;
  } else {
    plantId = existingPlant.id;
    // Increment discovery count
    await supabase
      .from('plants')
      .update({ discovery_count: existingPlant.discovery_count + 1 })
      .eq('id', plantId);
  }

  // Check if this user already discovered this species
  const { data: existingDiscovery } = await supabase
    .from('discoveries')
    .select('id')
    .eq('user_id', userId)
    .eq('plant_id', plantId)
    .single();

  if (existingDiscovery) {
    return { already_discovered: true, plant_id: plantId, xp_gained: 0, is_pioneer: false };
  }

  // Upload photo to Supabase Storage
  const photoPath = `discoveries/${userId}/${plantId}-${Date.now()}.jpg`;
  const photoBytes = Uint8Array.from(atob(photo_base64.replace(/^data:image\/\w+;base64,/, '')), c => c.charCodeAt(0));
  await supabase.storage.from('plant-photos').upload(photoPath, photoBytes, { contentType: 'image/jpeg' });
  const { data: { publicUrl } } = supabase.storage.from('plant-photos').getPublicUrl(photoPath);

  // Save discovery
  await supabase.from('discoveries').insert({
    user_id: userId,
    plant_id: plantId,
    photo_url: publicUrl,
    location_lat,
    location_lng,
    ai_confidence: confidence,
    is_pioneer: isPioneer,
  });

  // Calculate XP
  const xpGained = isPioneer ? 50 : 25;

  // Update user XP and pioneer count
  const { data: profile } = await supabase
    .from('profiles')
    .select('total_xp, pioneer_count')
    .eq('id', userId)
    .single();

  const newXp = (profile?.total_xp ?? 0) + xpGained;
  await supabase.from('profiles').update({
    total_xp: newXp,
    pioneer_count: isPioneer ? (profile?.pioneer_count ?? 0) + 1 : (profile?.pioneer_count ?? 0),
    level: xpToLevel(newXp),
  }).eq('id', userId);

  return {
    plant_id: plantId,
    plant,
    xp_gained: xpGained,
    is_pioneer: isPioneer,
    photo_url: publicUrl,
    already_discovered: false,
  };
}

function xpToLevel(xp: number): number {
  const thresholds = [0, 100, 250, 500, 1000, 2000, 4000, 8000];
  let level = 1;
  for (let i = 1; i < thresholds.length; i++) {
    if (xp >= thresholds[i]) level = i + 1;
    else break;
  }
  return level;
}
