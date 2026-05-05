from django.core.management.base import BaseCommand
from django.utils.text import slugify

from channels.models import Channel

CHANNELS = [
    (505, 'Sony Sports Ten 1 HD', 'https://ott1.viatv.com.np//images/channel/logo/Sony_Sports_Ten_1_HD.png', 'http://110.44.127.109:8081/viatv/viaten1hd/playlist.m3u8'),
    (506, 'Sony Sports Ten 2 HD', 'https://ott1.viatv.com.np//images/channel/logo/Sony_Sports_Ten_2_HD.png', 'http://110.44.127.109:8081/viatv/viaten2hd/playlist.m3u8'),
    (507, 'Sony Sports Ten 3 HD', 'https://ott1.viatv.com.np//images/channel/logo/Sony_Sports_Ten_3_HD.png', 'http://110.44.127.109:8081/viatv/viaten3hd/playlist.m3u8'),
    (508, 'Sony Sports Ten 5 HD', 'https://ott1.viatv.com.np//images/channel/logo/Sony_Sports_Ten_5_HD.png', 'http://110.44.127.109:8081/livesports/SonyTen5HD/playlist.m3u8'),
    (510, 'Star Sports 1 HD', 'https://ott1.viatv.com.np//images/channel/logo/Star_Sport_1_HD.jpg', 'http://110.44.127.109:8081/livesports/StarSpo1Hd.stream/playlist.m3u8'),
    (511, 'Star Sports 2 HD', 'https://ott1.viatv.com.np//images/channel/logo/Star_Sports_2_HD.jpg', 'http://110.44.127.109:8081/livesports/StarSport2HD/playlist.m3u8'),
    (512, 'Star Sports 1 HD Hindi', 'https://ott1.viatv.com.np//images/channel/logo/Star_Sports_1_HD_Hindi.jpg', 'http://110.44.127.109:8081/viatv/viaStarSp1HinDib.stream/playlist.m3u8'),
    (513, 'Star Sports Select 1 HD', 'https://ott1.viatv.com.np//images/channel/logo/Star_Sports_Select_1_HD.jpg', 'http://110.44.127.109:8081/viatv/viaselecthd/playlist.m3u8'),
    (514, 'Star Sports Select 2 HD', 'https://ott1.viatv.com.np//images/channel/logo/Star_Sports_Select_2_HD.jpg', 'http://110.44.127.109:8081/viatv/viaselecthd2/playlist.m3u8'),
    (515, 'Star Sports Select 1', 'https://ott1.viatv.com.np//images/channel/logo/Star_Sports_Select_1.jpg', 'http://110.44.127.109:8081/viatv/viaselect1sd/playlist.m3u8'),
    (516, 'Star Sports Select 2', 'https://ott1.viatv.com.np//images/channel/logo/Star_Sports_Select_2.jpg', 'http://110.44.127.109:8081/viatv/viachannelv/playlist.m3u8'),
    (524, 'Star Sports 1', 'https://ott1.viatv.com.np//images/channel/logo/Star_Sports_1.jpg', 'http://110.44.127.109:8081/viatv/viastarsports1sd/playlist.m3u8'),
    (525, 'Star Sports 2', 'https://ott1.viatv.com.np//images/channel/logo/Star_Sports_2.jpg', 'http://110.44.127.109:8081/viatv/viastarsports2sd/playlist.m3u8'),
    (526, 'Star Sports 1 Hindi', 'https://ott1.viatv.com.np//images/channel/logo/Star_Sports_1_Hindi.jpg', 'http://110.44.127.109:8081/viatv/viastarsports3sd/playlist.m3u8'),
    (527, 'DD SPORTS', 'https://ott1.viatv.com.np//images/channel/logo/DD_SPORTS.jpg', 'http://110.44.127.109:8081/viatv/viaddsports/playlist.m3u8'),
    (406, 'Star Movies HD', 'https://ott1.viatv.com.np//images/channel/logo/Star_Movies_HD.jpg', 'http://110.44.127.109:8081/viatv/viaStarMoviesHd.stream/playlist.m3u8'),
    (407, 'Star Movies Select HD', 'https://ott1.viatv.com.np//images/channel/logo/Star_Movies_Select_HD.jpg', 'http://110.44.127.109:8081/viatv/viaStarMovSelectHd.stream/playlist.m3u8'),
    (409, 'Sony Max HD', 'https://ott1.viatv.com.np//images/channel/logo/Sony_Max_HD.png', 'http://110.44.127.109:8081/viatv/viasonymaxhd/playlist.m3u8'),
    (410, 'COLORS CINEPLEX HD', 'https://ott1.viatv.com.np//images/channel/logo/COLORS_CINEPLEX_HD.jpg', 'http://110.44.127.109:8081/viatv/viacineplexhd/playlist.m3u8'),
    (411, '& Pictures HD', 'https://ott1.viatv.com.np//images/channel/logo/&_Pictures_HD.png', 'http://110.44.127.109:8081/viatv/viaandpicture/playlist.m3u8'),
    (412, 'Star Gold HD', 'https://ott1.viatv.com.np//images/channel/logo/Star_Gold_HD.jpg', 'http://110.44.127.109:8081/viatv/viastargoldhd/playlist.m3u8'),
    (413, 'ZEE CINEMA HD', 'https://ott1.viatv.com.np//images/channel/logo/ZEE_CINEMA_HD.png', 'http://110.44.127.109:8081/viatv/viazeecinemahd/playlist.m3u8'),
    (414, 'Star Gold Select HD', 'https://ott1.viatv.com.np//images/channel/logo/Star_Gold_Select_HD.jpg', 'http://110.44.127.109:8081/viatv/viastargoldselecthd/playlist.m3u8'),
    (416, 'Star Movies SD', 'https://ott1.viatv.com.np//images/channel/logo/Star_Movies_SD.png', 'http://110.44.127.109:8081/viatv/viastarmovies/playlist.m3u8'),
    (417, 'Star Gold SD', 'https://ott1.viatv.com.np//images/channel/logo/Star_Gold_SD.jpg', 'http://110.44.127.109:8081/viatv/viaStarGoldSD.stream/playlist.m3u8'),
    (418, 'Sony Max 2', 'https://ott1.viatv.com.np//images/channel/logo/Sony_Max_2.png', 'http://110.44.127.109:8081/viatv/viamaxtwo/playlist.m3u8'),
    (422, 'Zee Bollywood', 'https://ott1.viatv.com.np//images/channel/logo/Zee_Bollywood.png', 'http://110.44.127.109:8081/viatv/viazeecinema/playlist.m3u8'),
    (423, 'Star Gold 2', 'https://ott1.viatv.com.np//images/channel/logo/Star_Gold_2.jpg', 'http://110.44.127.109:8081/viatv/viamoviesok/playlist.m3u8'),
    (425, 'STAR GOLD SELECT SD', 'https://ott1.viatv.com.np//images/channel/logo/STAR_GOLD_SELECT_SD.png', 'http://110.44.127.109:8081/viatv/viaStarGoldSeleSD/playlist.m3u8'),
    (426, 'Zee Action', 'https://ott1.viatv.com.np//images/channel/logo/Zee_Action.png', 'http://110.44.127.109:8081/viatv/viazeeactionsd/playlist.m3u8'),
    (428, 'Sony PIx HD', 'https://ott1.viatv.com.np//images/channel/logo/Sony_PIx_SD.jpeg', 'http://110.44.127.109:8081/viatv/viasonypix/playlist.m3u8'),
    (438, 'Zee Classic', 'https://ott1.viatv.com.np//images/channel/logo/Zee_Classic.png', 'http://110.44.127.109:8081/viatv/vialivingfoodz/playlist.m3u8'),
    (449, 'Star Utsav Movies', 'https://ott1.viatv.com.np//images/channel/logo/Star_Utsav_Movies.png', 'http://110.44.127.109:8081/viatv/viastarutsav/playlist.m3u8'),
]


class Command(BaseCommand):
    help = 'Seed channel rows from curated M3U entries.'

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for channel_number, name, logo_url, stream_source_url in CHANNELS:
            slug = slugify(name)
            channel, is_created = Channel.objects.update_or_create(
                slug=slug,
                defaults={
                    'channel_number': channel_number,
                    'name': name,
                    'logo_url': logo_url,
                    'stream_source_url': stream_source_url,
                    'is_active': True,
                },
            )
            if is_created:
                created += 1
            else:
                updated += 1
            self.stdout.write(self.style.SUCCESS(f'Synced channel: {channel.name}'))
        self.stdout.write(self.style.SUCCESS(f'Done. Created={created}, Updated={updated}'))
