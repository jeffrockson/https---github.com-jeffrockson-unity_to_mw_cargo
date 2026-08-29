local p = {}



-- Cargo passes parameters with spaces instead of underscores
local DESCRIPTION_KEY = ("description_key_en"):gsub("_", " ")
local REPLACEMENT_KEYS = {
  "modifier",
  "seconds",
  ("biome_displayName_key_en"):gsub("_", " "),
  ("minDifficulty displayName key en"):gsub("_", " "),
  ("minDifficulty_shortName"):gsub("_", " "),
  ("category_displayName_key_en"):gsub("_", " "),
  ("payment_costPerPayment_amount"):gsub("_", " "),
  ("payment_costPerPayment_good"):gsub("_", " "),
  ("good_amount"):gsub("_", " "),
  ("good_good"):gsub("_", " "),
  "maxYear",
  "distance",
  "minDeaths",
  "minAttacks",
  "needsAmount",
  "relicsAmount",
  "amberTotalValue",
  "valueInAmbers",
  "regular",
  "dangerous",
  "forbidden",
  "amount"
}



--[[Notes:
"Jinxed" looks backwards
]]



local function _is_guid(replacement)
  return type(replacement) == "string" and #replacement == 32 and replacement:match("^%x{32}$") ~= nil
end



local function replace_placeholder(args)
  for _, key in ipairs(REPLACEMENT_KEYS) do
    if args[key] then
      local replacement = args[key]
      if _is_guid(replacement) then
        -- run cargo query 
    end
  end
end



function p.render( frame )
  local args = frame:getParent().args
  local description = args[DESCRIPTION_KEY]
  if not description or description == "" then
    return ""
  end
  -- if no placeholders like `{0}` or `{1}` then return the description as is
  description = description:gsub("{(%d+)}", replace_placeholder(args))
  return description
end



return p