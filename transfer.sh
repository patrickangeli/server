#!/bin/bash

# Script para download do Gofile
download_gofile() {
    url="$1"
    id=$(sed 's|.*gofile.io/d/||g' <<< "$url")
    
    # Obter token de conta convidado
    token=$(curl -s 'https://api.gofile.io/createAccount' | jq -r '.data.token')
    
    # Obter token do site
    websiteToken=$(curl -s 'https://gofile.io/dist/js/alljs.js' | grep 'fetchData.wt' | awk '{ print $3 }' | jq -r)
    
    # Obter informações do conteúdo
    resp=$(curl 'https://api.gofile.io/getContent?contentId='"$id"'&token='"$token"'&wt='"$websiteToken"'&cache=true')
    
    mkdir "$id" 2>/dev/null
    cd "$id"
    
    # Download dos arquivos
    for i in $(jq '.data.contents | keys | .[]' <<< "$resp"); do
        name=$(jq -r '.data.contents['"$i"'].name' <<< "$resp")
        download_url=$(jq -r '.data.contents['"$i"'].link' <<< "$resp")
        curl -H 'Cookie: accountToken='"$token" "$download_url" -o "$name"
    done
}

# Configurar rclone para OneDrive
rclone_setup() {
    rclone config create onedrive onedrive
}

# Transferir arquivos para OneDrive
upload_to_onedrive() {
    local source_dir="$1"
    local onedrive_folder="$2"
    rclone copy "$source_dir" "onedrive:$onedrive_folder" -P
}

# Execução principal
main() {
    local source_dir="$1"
    local onedrive_folder="$2"
    
    # Upload para OneDrive
    upload_to_onedrive "$source_dir" "$onedrive_folder"

    # Limpar arquivos temporários
    cd ..
    rm -rf "$id"
}

# Uso: ./script.sh PASTA_LOCAL PASTA_ONEDRIVE
main "$1" "$2"
